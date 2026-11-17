"""Pure validation, readiness and admission contracts for the SZL model host.

No network, filesystem or tensor operations occur in this module.  ``loaded``
describes residency only: readiness additionally requires explicit identity and
canary evidence for every model assigned to the host.
"""

from __future__ import annotations

from collections import deque
from collections.abc import Iterable, Mapping
from contextlib import contextmanager
import math
import re
import threading
import time


class ContractError(ValueError):
    """A client/configuration error with a safe machine-readable code."""

    def __init__(self, code: str, message: str):
        self.code = code
        super().__init__(message)


def _positive_int(value, name: str, *, minimum: int = 1) -> int:
    if type(value) is not int or value < minimum:
        raise ContractError("invalid_limit", f"{name} must be an integer >= {minimum}")
    return value


def _relative_parts(path: str) -> tuple[str, ...]:
    if not isinstance(path, str) or not path:
        raise ContractError("invalid_artifact_path", "Artifact paths must be nonempty strings")
    if "\\" in path or ":" in path or any(ord(c) < 32 or ord(c) == 127 for c in path):
        raise ContractError("invalid_artifact_path", "Artifact path contains a forbidden character")
    parts = tuple(path.split("/"))
    if any(part in ("", ".", "..") for part in parts):
        raise ContractError("invalid_artifact_path", "Artifact path must be a normalized relative POSIX path")
    return parts


def choose_adapter_config(files: Iterable[str]) -> str:
    """Choose one exact ``adapter_config.json`` path, never a directory scan.

    Every input path is validated.  Non-checkpoint releases retain the existing
    shallowest-path then lexical precedence.  If only numbered checkpoints are
    present, select the highest numeric step; ties use depth then lexical order.
    A checkpoint directory must be named exactly ``checkpoint-<digits>``.
    """
    if isinstance(files, (str, bytes)):
        raise ContractError("invalid_artifact_paths", "Expected an iterable of relative paths")
    try:
        paths = list(files)
    except TypeError as exc:
        raise ContractError("invalid_artifact_paths", "Expected an iterable of relative paths") from exc
    releases = []
    checkpoints = []
    for path in paths:
        parts = _relative_parts(path)
        if parts[-1] != "adapter_config.json":
            continue
        checkpoint_parts = [part for part in parts[:-1] if part.startswith("checkpoint-")]
        if not checkpoint_parts:
            releases.append(path)
            continue
        if any(re.fullmatch(r"checkpoint-[0-9]+", part) is None for part in checkpoint_parts):
            raise ContractError("invalid_checkpoint_path", "Checkpoint directories require numeric steps")
        step = max(int(part.split("-", 1)[1]) for part in checkpoint_parts)
        checkpoints.append((step, path))
    if releases:
        return min(releases, key=lambda path: (path.count("/"), path))
    if checkpoints:
        return min(checkpoints, key=lambda item: (-item[0], item[1].count("/"), item[1]))[1]
    raise ContractError("adapter_config_missing", "No adapter_config.json exists in the file list")


def validate_generation_request(req, max_prompt_chars: int = 16384,
                                max_new_tokens: int = 512) -> tuple[str, str, int]:
    """Validate serving inputs and optional expected identity; ignore extra fields.

    ``model`` and ``prompt`` are required strings. Empty prompts are accepted
    for compatibility; empty/whitespace model names are not. The output-token
    default is min(256, the configured ceiling). No coercion or truncation occurs.
    """
    _positive_int(max_prompt_chars, "max_prompt_chars")
    _positive_int(max_new_tokens, "max_new_tokens")
    if not isinstance(req, dict):
        raise ContractError("invalid_request", "The request body must be a JSON object")
    model = req.get("model")
    if (not isinstance(model, str) or not model.strip() or model != model.strip()
            or len(model) > 256 or any(ord(c) < 32 or ord(c) == 127 for c in model)):
        raise ContractError("invalid_model", "model must be a nonempty identifier of at most 256 characters")
    prompt = req.get("prompt")
    if not isinstance(prompt, str):
        raise ContractError("invalid_prompt", "prompt must be a string")
    if len(prompt) > max_prompt_chars:
        raise ContractError("prompt_too_large", "prompt exceeds the configured character limit")
    count = req.get("max_new_tokens", min(256, max_new_tokens))
    if type(count) is not int or not 1 <= count <= max_new_tokens:
        raise ContractError("invalid_max_new_tokens", "max_new_tokens must be an integer within the configured limits")
    expected = req.get("expected_artifact_fingerprint")
    if ("expected_artifact_fingerprint" in req
            and (not isinstance(expected, str) or re.fullmatch(r"[0-9a-f]{64}", expected) is None)):
        raise ContractError("invalid_expected_artifact_fingerprint", "Expected identity must be a lowercase SHA256 digest")
    return model, prompt, count


def _manifest_name(entry) -> str:
    if isinstance(entry, str):
        raw = entry
    elif isinstance(entry, Mapping):
        raw = entry.get("name") or entry.get("repo_id") or entry.get("repo")
    else:
        raw = None
    if not isinstance(raw, str) or not raw or raw != raw.strip():
        raise ContractError("invalid_manifest", "Every manifest entry needs a name or repository ID")
    return _relative_parts(raw)[-1]


def _valid_measurement(value) -> bool:
    if type(value) is int:
        return value >= 0
    return type(value) is float and math.isfinite(value) and value >= 0


def readiness_summary(expected_manifest: Iterable, model_states: Mapping, *,
                      free_disk_bytes=None, free_vram_mb=None,
                      min_free_disk_bytes=50 * 1024**3, min_free_vram_mb=4000,
                      intentional_exclusions: Iterable[str] = (),
                      initialization_complete: bool = True) -> dict:
    """Return evidence-based readiness without changing serving/model state.

    Manifest entries may be names, repo IDs or mappings with name/repo_id/repo.
    State keys are normalized the same way. State values are status strings or
    mappings. An assigned model is verified only when its status is ``loaded``
    or ``ready`` AND ``identity_verified`` and ``canary_ok`` are literally True.
    Unknown/nonfinite/negative resource measurements fail readiness closed.
    Exclusions must name manifest entries; duplicate names are configuration errors.
    The caller owns canary freshness and should set canary_ok=False when stale.
    """
    if isinstance(expected_manifest, (str, bytes)) or not isinstance(model_states, Mapping):
        raise ContractError("invalid_manifest", "Expected a manifest iterable and a state mapping")
    names = [_manifest_name(entry) for entry in expected_manifest]
    if len(names) != len(set(names)):
        raise ContractError("duplicate_model_name", "Manifest model names must be unique")
    expected = set(names)
    if isinstance(intentional_exclusions, (str, bytes)):
        raise ContractError("invalid_exclusions", "Expected an iterable of excluded model names")
    excluded = {_manifest_name(entry) for entry in intentional_exclusions}
    if not excluded <= expected:
        raise ContractError("unknown_exclusion", "Exclusions must belong to the configured manifest")
    states = {}
    for name, value in model_states.items():
        normalized = _manifest_name(name)
        if normalized in states:
            raise ContractError("duplicate_model_name", "State model names must be unique")
        states[normalized] = value
    if type(initialization_complete) is not bool:
        raise ContractError("invalid_initialization_state", "initialization_complete must be boolean")
    if not _valid_measurement(min_free_disk_bytes) or not _valid_measurement(min_free_vram_mb):
        raise ContractError("invalid_limit", "Resource thresholds must be finite and nonnegative")
    required = expected - excluded
    loaded, verified, unavailable = set(), set(), {}
    for name in expected & states.keys():
        state = states[name]
        status = state.get("status") if isinstance(state, Mapping) else state
        if status in ("loaded", "ready"):
            loaded.add(name)
            if (isinstance(state, Mapping) and state.get("identity_verified") is True
                    and state.get("canary_ok") is True):
                verified.add(name)
        elif name in required:
            # Do not expose raw exception strings stored after the status prefix.
            safe_status = status.split(":", 1)[0] if isinstance(status, str) else "unknown"
            unavailable[name] = safe_status if re.fullmatch(r"[a-zA-Z0-9_-]{1,64}", safe_status) else "unknown"
    missing = required - states.keys()
    unverified = (required & loaded) - verified
    unexpected = states.keys() - expected
    resources = {
        "disk": {"free_bytes": free_disk_bytes if _valid_measurement(free_disk_bytes) else None,
                 "minimum_bytes": min_free_disk_bytes},
        "vram": {"free_mb": free_vram_mb if _valid_measurement(free_vram_mb) else None,
                 "minimum_mb": min_free_vram_mb},
    }
    reasons = []
    if not initialization_complete:
        reasons.append("initialization_incomplete")
    if not required:
        reasons.append("no_required_models")
    if missing:
        reasons.append("required_models_missing")
    if unavailable:
        reasons.append("required_models_unavailable")
    if unverified:
        reasons.append("required_models_unverified")
    if unexpected:
        reasons.append("unexpected_models_observed")
    for label, value, threshold in (("disk", free_disk_bytes, min_free_disk_bytes),
                                    ("vram", free_vram_mb, min_free_vram_mb)):
        if not _valid_measurement(value):
            reasons.append(label + "_measurement_unavailable")
        elif value < threshold:
            reasons.append(label + "_below_reserve")
    ready = not reasons
    return {
        "ready": ready, "http_status": 200 if ready else 503,
        "configured_count": len(expected), "required_count": len(required),
        "loaded_count": len(loaded), "verified_count": len(verified),
        "excluded_count": len(excluded), "required": sorted(required),
        "loaded": sorted(loaded), "missing": sorted(missing),
        "unavailable": dict(sorted(unavailable.items())), "unverified": sorted(unverified),
        "intentional_exclusions": sorted(excluded), "unexpected": sorted(unexpected),
        "reasons": reasons, "resources": resources,
    }


class AdmissionRejected(RuntimeError):
    def __init__(self, code: str):
        self.code = code
        super().__init__(code)


class BoundedAdmission:
    """FIFO admission gate with a strict active + waiting request bound.

    Use ``with gate.slot(timeout=0.5): ...``. A full queue raises ``busy``;
    expiry raises ``queue_timeout``. This bounds admitted/waiting work, not the
    HTTP server's thread creation; enforce socket/body bounds at the listener too.
    """

    def __init__(self, max_inflight: int = 1, max_queue: int = 2):
        self.max_inflight = _positive_int(max_inflight, "max_inflight")
        self.max_queue = _positive_int(max_queue, "max_queue", minimum=0)
        self._condition = threading.Condition()
        self._active = 0
        self._waiting = deque()

    def acquire(self, timeout: float = 0.0) -> bool:
        if not _valid_measurement(timeout):
            raise ContractError("invalid_timeout", "timeout must be finite and nonnegative")
        deadline = time.monotonic() + timeout
        with self._condition:
            if self._active < self.max_inflight and not self._waiting:
                self._active += 1
                return True
            if timeout == 0 or len(self._waiting) >= self.max_queue:
                raise AdmissionRejected("busy")
            ticket = object()
            self._waiting.append(ticket)
            try:
                while True:
                    remaining = deadline - time.monotonic()
                    if remaining <= 0:
                        raise AdmissionRejected("queue_timeout")
                    if self._waiting[0] is ticket and self._active < self.max_inflight:
                        self._waiting.popleft()
                        self._active += 1
                        self._condition.notify_all()
                        return True
                    self._condition.wait(remaining)
            finally:
                if ticket in self._waiting:
                    self._waiting.remove(ticket)
                    self._condition.notify_all()

    def release(self) -> None:
        with self._condition:
            if self._active <= 0:
                raise RuntimeError("Admission release without an active request")
            self._active -= 1
            self._condition.notify_all()

    @contextmanager
    def slot(self, timeout: float = 0.0):
        self.acquire(timeout)
        try:
            yield
        finally:
            self.release()

    def snapshot(self) -> dict:
        with self._condition:
            return {"active": self._active, "queued": len(self._waiting),
                    "max_inflight": self.max_inflight, "max_queue": self.max_queue}
