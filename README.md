# szl-serve

**Historical Khipu evidence, offline proposal validation, and governed Atelier migration.**

KERNEL-owned canonical governed-inference **recipe + validator + energy receipt** for SZL Holdings.

<!-- szl:header v1 -->
<!-- Native identity: szl-brand@4309f6fce89179331b0b3ed8c99494e76c5be256; Orbit v2 icon. -->
<p>
  <a href="https://github.com/szl-holdings">
    <img src="https://raw.githubusercontent.com/szl-holdings/szl-brand/4309f6fce89179331b0b3ed8c99494e76c5be256/kit/logos/orbit-v2/suite/szl-icon-32.svg" alt="SZL Holdings — Orbit v2" width="32" height="32" />
  </a>
</p>

**Control before action. Evidence after.**

[Product](https://a-11-oy.com) · [Proof](https://a11oy.net) · [GitHub organization](https://github.com/szl-holdings)
<!-- /szl:header -->

This is **not** a vendor engine. It is the silhouette of 2026 serving (vLLM / SGLang / TGI / TensorRT-LLM / llama.cpp / Dynamo) — without copying those engines, and without fabricating tokens/s or joules.

Homepage: [a-11-oy.com](https://a-11-oy.com) · Owner: Stephen P. Lutar Jr. / SZL Holdings · Doctrine v11 LOCKED **749/14/163** · Λ = **Conjecture 1** (advisory, never a theorem) · Apache-2.0

---

## What this is NOT

- **Not vLLM. Not TGI. Not TensorRT-LLM. Not SGLang. Not Dynamo.** Those names are the 2026 silhouette. This repo does not vendor-copy them. GPU path is **ROADMAP** until MEASURED on named hardware.
- **Not a tokens/s leaderboard.** A MEASURED sample is raw completion tokens + `elapsed_ms`. No derived tok/s rating.
- **Not proven trust.** A hash-chained receipt proves integrity of that record. It does not prove the model, the lab, or Λ.
- **Not a takeover of the Hugging Face Space.** FORGE owns [`szl-holdings/szl-forge`](https://github.com/szl-holdings/szl-forge) / [`SZLHOLDINGS/szl-model-inference-lab`](https://huggingface.co/spaces/SZLHOLDINGS/szl-model-inference-lab). This KERNEL repo preserves its historical artifact and source pins. The old OpenAI chat route is **RETIRED**; the dated measurement does not establish current serving.
- **Not [`szl-forge-lab`](https://huggingface.co/spaces/SZLHOLDINGS/szl-forge-lab).** That Space is **SNAPSHOT / READ-ONLY**, not a trainer, not a serve runtime. Do not point `szl-serve` at forge-lab.
- **Not Ask & Act as a live control plane.** The a11oy operator tab does not gate, launch, or control this recipe.
- **Not energy-attested-runs as MEASURED serve energy.** That corpus is **8/8 SIMULATED**, not an NVML joule delta and not a live serve path.

Honesty plate: [`CARD.md`](CARD.md).

---

## ATELIER lock

The historical backend is `SZLHOLDINGS/szl-model-inference-lab`. Its old OpenAI
route is **RETIRED**. Generation moves through the existing authenticated A11oy
Atelier form at `/command-centre#cpu-work` on your verified A11oy deployment.
This package prints navigation; it does not submit or forward prompts. See the
[migration contract](docs/atelier-migration.md).

| Surface | Class |
|---|---|
| `SZLHOLDINGS/szl-model-inference-lab` | Read-only identity surfaces; legacy chat **RETIRED** |
| A11oy `/command-centre#cpu-work` | Operator form; deployment availability **NOT_PROBED** by this package |
| `SZLHOLDINGS/szl-forge-lab` | **SNAPSHOT**, not a trainer, **not a serve target** |
| GPU / vLLM / TGI / TensorRT-LLM / SGLang / Dynamo | **ROADMAP** |
| `SZLHOLDINGS/energy-attested-runs` | **8/8 SIMULATED** — not this recipe's CPU energy evidence |
| Ask & Act | **not a live control plane** |

---

## Historical CPU measurement — 2026-11-04

This immutable sample records the old route. It remains historical evidence;
it is not evidence that the route is available now.

| | |
|---|---|
| Surface | https://szlholdings-szl-model-inference-lab.hf.space |
| Space | https://huggingface.co/spaces/SZLHOLDINGS/szl-model-inference-lab |
| Historical FORGE source | [`e28abe9d4be3ce5efbb09ea2a3a248494c654636`](https://github.com/szl-holdings/szl-forge/tree/e28abe9d4be3ce5efbb09ea2a3a248494c654636/spaces/szl-model-inference-lab) |
| Historical API | `POST /v1/chat/completions` — now **RETIRED**, HTTP 410 |
| Model | `SZLHOLDINGS/SZL-Khipu-1.5B-GGUF@67d60ec577730747055491640cfb91fc4a4b5d25` |
| GGUF | `SZL-Khipu-1.5B-Q4_K_M.gguf` · SHA-256 `13c1a1993063e1dff92f7413ccf48eaca6d48efc8801ae9af35961ae3396623a` · 986047904 bytes |
| Sample 2026-11-04 | **24** completion tokens · **elapsed_ms 8237** · execution_record **UNSIGNED** · evidence [`measured-cpu-serve-20261104.json`](evidence/measured-cpu-serve-20261104.json) |
| Energy | `joules=null` · label **UNAVAILABLE** (CPU lab; MEASURED only from a real NVML delta) |
| GPU | **ROADMAP** until MEASURED on named hardware |
| Availability | Historical sample only; no current generation or SLA claim |

There is no replacement OpenAI curl. `live_openai_curl()` now raises
`RetiredRecipeError` and never echoes or forwards a prompt. Compatibility
metadata keeps the legacy `live` / `live_cpu` keys with `status="RETIRED"`,
`available=false`, and `curl=null`; the recipe document is version 2.

The authenticated A11oy API is `POST /api/a11oy/v1/atelier/cpu-lab/turn`.
It requires an operator bearer, `prompt`, `declared: "PUBLIC"`, explicit
`public_share_acknowledged: true` for that prompt, and `max_output_tokens <= 32`.
Use the form by default. The [API migration example](docs/atelier-migration.md)
contains only a credential placeholder and creates no second execution client.
Grounding is required; output is proposal-only with no tool or action authority.

Contract: `/.well-known/szl-inference-contract.json`. Identity: `/api/v1/identity`.

---

## Read-only runtime qualification

The pinned recipe can drift from the public Space. `qualify` reads four bounded
JSON surfaces and emits one receipt with per-field `OBSERVED`, `DIVERGENT`, or
`UNKNOWN` states:

```bash
szl-serve qualify --output qualification.json
```

The command checks `/api/build-info`, `/api/v1/identity`,
`/.well-known/szl-inference-contract.json`, and `/v1/models`. It requires the
exact Forge source repository and revision, model revision, GGUF file, byte
count, SHA-256, contract schema, and model-list identity. A timeout, partial
JSON, HTML response, oversized response, cross-origin redirect, missing field,
or stale value never becomes success. The current public contract may report
`UNKNOWN` for source repository until `/api/build-info` exposes that field;
the qualifier does not infer it from a URL or Space name. Historical pins are
not updated merely to make a divergent current runtime pass.

Identity `state` remains separate from `legacy_route.state`. The latter observes
the exact route declarations in both identity and contract, including retirement
or conflicting declarations. Known retirement survives a failed metadata read.
`serving_ready` is always `false` and `serving_state` is `NOT_QUALIFIED`: metadata
cannot establish successful inference or validated output. These fields are
included in the receipt hash.

CLI exit 2 means the legacy route is retired or its declarations conflict.
Exit 1 means identity fields are unknown/divergent or route declarations are
incomplete/unknown. Exit 0 requires observed pinned identity fields and complete,
consistent, nonretired route declarations. **No exit code means serving is
qualified.**

Qualification is read-only. It sends no prompt, mints no signed release
receipt, changes no provider state, and says nothing about response quality,
safety, SLA, or production readiness.

---

## Airgap twin — unqualified local llama.cpp / Ollama templates

These commands select a Hub quant label. Verify the downloaded bytes against
the immutable SHA-256 pin before use. The templates do not establish local
serving readiness, hardware qualification, or current artifact availability.

```bash
llama-cli    -hf SZLHOLDINGS/SZL-Khipu-1.5B-GGUF:Q4_K_M
llama-server -hf SZLHOLDINGS/SZL-Khipu-1.5B-GGUF:Q4_K_M
ollama run hf.co/SZLHOLDINGS/SZL-Khipu-1.5B-GGUF:Q4_K_M
```

Print navigation, historical metadata, and unqualified local command templates
(no executable public request or GGUF download):

```bash
python -m szl_serve recipe
```

Local command strings target POSIX shells (`sh`/Bash). Prompts and server
host/port values are quoted as literal arguments;
shell substitutions inside them are not executed. PowerShell and `cmd.exe`
use different quoting rules and are not supported by these command generators.
The generators print recipes only; the selected engine validates host/port values.

---

## Controller — schema outside the weights

Model output is **proposal-only**. Copy of [`khipu.schema.json`](schemas/khipu.schema.json) is pinned from the GGUF repo (SHA-256 `b95f9927366dae7c5d36cfb7de6e229eb605524318ab642a6aa2292a212170d0`).

Built wheels include this exact 6,262-byte schema and its `PIN.json` under
`szl_serve/schemas/`. The validator prefers these package resources; source
checkouts use the canonical root `schemas/` copy. Git preserves LF bytes for
both JSON files on Windows as well as Linux. Schema bytes and the SHA-256 pin
remain strict: a drifted packaged schema is rejected, rather than normalized
or replaced with a fallback copy.

- Hallucinated `citedNodeIds` → **REJECT**. Never silently repaired into a green plan.
- `brainBinding.status` stays **NOT_RESOLVED**.
- Real model output provenance is **MODEL_PROPOSED**, not `SYNTHETIC`.
- Calls using `source="MODEL"` require controller-provided `offered_ids`;
  the model's own candidate list cannot establish grounding. An empty list
  explicitly means no handles were offered and still enforces rejection.
- Invalid JSON / cross-field contract failure → fail closed (`REJECT`).

The CLI examples below check schema and internal consistency (`source="UNKNOWN"`).
They do not establish that handles were independently offered to a real model.

```bash
python -m szl_serve validate tests/fixtures/plan_model_proposed.json
python -m szl_serve validate tests/fixtures/plan_hallucinated_cited.json   # exits 1
```

---

## Energy + receipt

Each wrap uses `szl-energy-attest` semantics (import if available, else a tiny honest local meter):

| Energy | When |
|---|---|
| **MEASURED** | Real NVML energy-counter delta. `joules` is that number. |
| **UNAVAILABLE** | No GPU / no fresh NVML delta (the CPU lab and this CI). `joules=null`. |

Never invent a joule. Hash-chain a serve receipt: request hash, output hash, model pin, energy label. Receipt is **UNSIGNED** unless a key is actually present. Do not fake DSSE.

---

## MEASURED vs ROADMAP vs UNAVAILABLE

| Surface | Label |
|---|---|
| Public OpenAI chat recipe | **RETIRED** — HTTP 410; no generated request |
| CPU sample dated 2026-11-04 | Historical **MEASURED** evidence; not current availability |
| Khipu GGUF identity | **PINNED** artifact metadata; not serving qualification |
| A11oy Atelier operator form/API | **NOT_PROBED** by this package; explicit authentication and public acknowledgement required |
| llama.cpp / Ollama command templates | **UNQUALIFIED recipe**; verify artifact bytes before use |
| Energy on CPU | **UNAVAILABLE** |
| GPU / vLLM / TGI / TensorRT-LLM / SGLang / Dynamo | **ROADMAP** |
| GPU attention | **ROADMAP** — no fused/paged-attention LIVE claim; no tokens/s invented |
| Speculative decode (`szl-specdecode`) | **SPECDECODE=UNAVAILABLE** until soft-import LIVE — see below |
| `SZLHOLDINGS/szl-forge-lab` | **SNAPSHOT** — not a trainer; do not point this recipe at it |
| `SZLHOLDINGS/energy-attested-runs` | **8/8 SIMULATED** — not MEASURED NVML; not a live serve path |
| Ask & Act | **not a live control plane** |
| Chaski, ReceiptAgent weights | **ROADMAP** stubs on this config surface — not fake LIVE |

Λ is Conjecture 1. It does not become a theorem because a chat call returned 21 tokens.

---

## Speculative decode silhouette (optional)

Pointer to [`szl-holdings/szl-specdecode`](https://github.com/szl-holdings/szl-specdecode) (HF twin [`SZLHOLDINGS/szl-specdecode`](https://huggingface.co/SZLHOLDINGS/szl-specdecode)). Soft-imports `szl_specdecode.verify_draft` when that package is installed; otherwise labels **SPECDECODE=UNAVAILABLE**. GPU draft kernels stay **UNAVAILABLE**. Speedup claim stays **null** until a MEASURED draft/target pair receipt exists. Not a rehost of Medusa, EAGLE, TensorRT-LLM speculative decoding, or vLLM. Credit Stephen Lutar. MEASURED-or-null.

```python
from szl_serve.specdecode import probe_specdecode, get_verify_draft

probe_specdecode()           # {"label": "SPECDECODE=UNAVAILABLE", ...} or import-LIVE
get_verify_draft()           # callable or None — never fabricates tokens/s
```

---

## Tests

Unit tests use fixture plan JSON. **No network. Do not download the ~1 GB GGUF in CI.**
The packaging regression builds a wheel and an sdist-to-wheel round trip with
installed build tools and no package index, then installs the wheel into a
temporary target. An isolated Python subprocess outside the checkout checks
the exact schema and pin, validates a benign synthetic ABSTAIN proposal, and
confirms that tampered package data fails closed. Build tooling is a test extra.

```bash
python -m pip install --require-hashes -r requirements/test.lock
python -m pip install --no-deps -e .
pytest -q
```

`requirements/test.lock` is a universal hash-locked closure generated from the
published package metadata at the declared Python 3.10 floor, with an
`exclude-newer` cutoff of 2026-11-02 UTC.
Library compatibility ranges remain in `pyproject.toml`; the lock controls CI
and review reproduction without narrowing downstream consumers.

---

## Layout

```
LICENSE                 Apache-2.0, Copyright 2026 SZL Holdings
README.md               this Series A face
CARD.md                 honesty plate
schemas/khipu.schema.json
szl_serve/{__init__,schema,energy,recipe,cli}.py
tests/fixtures/*.json
```

---

<div align="center">

**Governed AI you can pin — not a leaderboard you can fake.**

[a-11-oy.com](https://a-11-oy.com) · [Khipu GGUF](https://huggingface.co/SZLHOLDINGS/SZL-Khipu-1.5B-GGUF) · [Historical CPU lab (FORGE)](https://huggingface.co/spaces/SZLHOLDINGS/szl-model-inference-lab)

<sub>SLSA: L1 honest · L2 attested · L3 roadmap. Λ = Conjecture 1. Trust ceiling 0.97 — never 100%.</sub>

</div>

## Massed GPU operator deployment

The separately deployed Massed Transformers/PEFT service is tracked under
[`deploy/modelhost`](deploy/modelhost/README.md), with immutable artifact locks,
bounded serving, encrypted SSH operator access, and per-host operational evidence.
This deployment has its own readiness gates and does not change the CPU recipe,
its public studio, or the roadmap status of the vendor-engine integrations.
