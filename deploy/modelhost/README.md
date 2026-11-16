# Massed modelhost deployment

This directory owns the separately deployed Transformers/PEFT modelhost on the
Massed GPU machines. The repository's pinned CPU recipe remains a separate
surface. This deployment does not claim a vendor serving engine, model quality,
an SLA, signed provenance, or measured energy.

## Serving contract

The runtime loads only local files listed in a frozen lock. Adapter selection is
the exact selected release/checkpoint directory; it never recursively selects a
different cached adapter. Base weights, tokenizer files, adapter configuration,
and adapter weights are pinned by repository revision, byte count, and actual
SHA-256. A base is shared only for the same repository and revision.

| Endpoint | Meaning |
| --- | --- |
| `GET /health` | Process liveness, boot identity, and resident models |
| `GET /ready` or `/readyz` | HTTP 200 only when all assigned models have verified identities and fresh operational canaries, initialization is complete, and resource reserves hold; otherwise 503 with reasons |
| `GET /models` | Versioned catalog including all configured entries, explicit exclusions, pins, canaries, and failures |
| `POST /generate` | Bounded generation for an already loaded model; no downloads or lazy loading |

The v2 `/models` response has a `models` object rather than the former flat map.
`/health` retains its legacy `loaded` and `free_mb` fields. Uploaded heartbeats
retain `loaded`, `statuses`, `free_mb`, and `gpu` alongside v2 evidence.

Generation requires `model` and `prompt`; `max_new_tokens` defaults to 256.
`expected_artifact_fingerprint` optionally pins the exact artifact identity.
Invalid fingerprints are rejected, and a valid but different fingerprint yields
409 before GPU work. Responses include the actual artifact fingerprint, model
revision, boot ID, request ID, completion-token count, and elapsed milliseconds.
Equal names on different machines do not imply equal checkpoints. There is no
automatic cross-host failover.

Default limits are 64 KiB request bodies, 16,384 prompt characters, 2,048 input
tokens, 256 new tokens, one active generation, two queued generations, eight HTTP
workers, a two-second queue wait, and a ten-second socket read timeout. Generation
has a 60-second cooperative Transformers limit. An unresponsive CUDA operation
cannot safely be killed inside the process; the generation gate stays occupied
until the operation exits. These controls do not constitute a latency SLA.

## Identity and readiness

`locks/gate1.json` and `locks/cuda.json` preserve the configured 49-entry
denominator. `khipu-abstain-r3-candidate` is explicitly classified as a metadata
repository: at the recorded revision it contains a README and evaluation report,
with no model weights. CUDA additionally excludes the three 4B adapter placements
to preserve the existing protected workload's VRAM. These are disclosed
assignment decisions; exclusions are never counted as loaded models.

The disk reserve is 50 GiB. Gate1 retains a 6,000 MiB VRAM reserve and CUDA retains
4,000 MiB. A disk-pressure 503 must remain visible until capacity is actually
restored; do not lower a threshold to manufacture a successful readiness result.

Every loaded adapter receives a one-token boot canary. A successful canary proves
only that the pinned serving path executed. It does not establish model quality,
correctness, safety, or suitability. Canary records contain token count, output
hash, duration, and time without prompt/output content. Idle canary refresh runs
every six hours; records older than 24 hours cease to establish readiness.

Local receipts are atomically replaced every 60 seconds with mode 0600 and contain
source/lock hashes, boot identity, full coverage, resource readings, and counters.
Optional existing Hub telemetry runs independently every 600 seconds. Records
are unsigned observations. No signing key or attestation is invented.

## Freeze an existing cache

Freeze does not contact the Hub and never downloads weights:

```bash
python freeze_cache.py \
  --config /home/Ubuntu/szl-modelhost/host_config.json \
  --cache /home/Ubuntu/szl-modelhost/hf/hub \
  --exclusion-policy /path/to/reviewed-exclusion-policy.json \
  --output /path/to/release/model_lock.json
```

The exclusion policy is a JSON object mapping configured model names to explicit
reasons. Missing files remain in the lock with an unavailable status. A metadata
repository exclusion also needs an independently recorded repository revision
and file-list observation, as shown in the checked-in deployment locks.

Do not commit a live `host_config.json`, SSH private key, Hub token, origin token,
Cloudflare service token, or unsanitized configuration. The runtime dependencies
are installed in the existing host virtual environments; recorded versions are
observations, not a new dependency installation or an upstream reproducibility
claim.

## Secure operator access

The modelhost binds to `127.0.0.1` by default. `fleet_client.py` uses the existing
trusted SSH host keys and named operator key to call that loopback listener over
an encrypted SSH channel. It rejects unknown host keys, never interpolates the
prompt into a shell command, selects one host explicitly, and checks the returned
artifact identity. It does not silently retry a generation on another machine.

```powershell
python deploy/modelhost/fleet_client.py inventory --host gate1
python deploy/modelhost/fleet_client.py generate --host gate1 --model chaski-r2 --prompt-file C:\SZL\prompt.txt --max-new-tokens 32
```

The default host is Gate1. Use `--host cuda` for an intentional CUDA call. The
client uses `~/.ssh/szl_massed_a6000_ed25519` unless an explicit key path is
provided. Inventory includes the actual readiness HTTP status and reasons.

An authenticated public hostname is a separate deployment gate. Before enabling
one, verify a narrowly scoped Access application and Service Auth policy, then
configure connector-side Access JWT validation for that application's audience.
Verify unauthenticated rejection, authorized inference, and origin bypass
closure. Preserve the unrelated ThinLinc and laptop mesh tunnels. A healthy
connector alone does not establish any of these properties.

## Staged activation and rollback

Stage source, contract, lock, and private configuration in a versioned release
directory. Compile and run the fixture tests first. Activate one host at a time
through a named systemd drop-in, keeping the prior unit/source/configuration
available. Do not start a second full modelhost on the same GPU during testing.

For the `20261116-identity-v2` release, the service override is
`/etc/systemd/system/szl-modelhost.service.d/70-identity-v2.conf`. It points at the
versioned release, uses the existing virtual environment, binds through the
release's loopback configuration, and sends output to the journal rather than
duplicating it into the former unbounded file log.

Rollback only this release's override, then reload and restart this one service:

```bash
sudo mv /etc/systemd/system/szl-modelhost.service.d/70-identity-v2.conf \
  /etc/systemd/system/szl-modelhost.service.d/70-identity-v2.conf.disabled
sudo systemctl daemon-reload
sudo systemctl restart szl-modelhost.service
```

The old source/configuration remain at their original paths. A rollback restores
the old listener behavior, including its public binding, so it is a recovery
operation requiring a follow-up exposure check. Do not alter protected Bonsai,
Colibri, Hatun, SSH, training services, or unrelated systemd overrides.

## Cache consolidation

`deduplicate_cache.py` audits an explicit plan by default. `--apply` atomically
replaces only a reviewed duplicate with a hardlink after both actual hashes,
immutable permissions, stable metadata, ownership, and filesystem identity pass.
Cache blob filenames are not accepted as content hashes. Symlink paths and
writable files are rejected. Repeated application is idempotent.

This is appropriate only for verified immutable, quiescent cache blobs. It does
not delete unique model stores or training artifacts. Future cache maintenance
must continue treating these blobs as immutable. Deleting one cache entry does
not delete the other hardlink's data.

## Verification

```bash
python -m unittest discover -s deploy/modelhost -p 'test_*.py' -q
pytest -q
```

Fixture tests exercise selection, identity mismatches, cache mutation, token/body
limits, worker/queue bounds, failed and stale canaries, exclusions, receipt writes,
and safe consolidation. The release evidence separately records actual host
loading, canaries, representative generation, direct-port closure, and protected
service observations. Fixture tests alone never establish CUDA readiness.
