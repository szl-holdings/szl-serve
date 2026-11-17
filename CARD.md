# Honesty plate — szl-serve
# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 SZL Holdings · Stephen P. Lutar Jr.

**KERNEL-owned canonical serve recipe + validator + energy receipt.**
Not a vendor engine. Not a takeover of the Hugging Face Space.

| Axis | Label | Fact |
|---|---|---|
| Historical backend | **PINNED** | `SZLHOLDINGS/szl-model-inference-lab`. The source pin records historical evidence, not current readiness. Do not point `szl-serve` at forge-lab. |
| Public OpenAI subset | **RETIRED** | `POST /v1/chat/completions` returns HTTP 410. No executable recipe or automatic forwarding remains. |
| A11oy Atelier migration | **NOT_PROBED** | Existing authenticated form `/command-centre#cpu-work`; exact operator/public acknowledgement contract in [migration documentation](docs/atelier-migration.md). Proposal-only; no tool or action authority. |
| Weight identity | **PINNED** | `SZL-Khipu-1.5B-Q4_K_M.gguf` · LFS SHA-256 `13c1a1993063e1dff92f7413ccf48eaca6d48efc8801ae9af35961ae3396623a` · 986047904 bytes |
| Sample 2026-11-04 | **MEASURED** | 24 completion tokens · `elapsed_ms` 8237 · execution_record **UNSIGNED**. Not a tokens/s rating. Receipt: [`evidence/measured-cpu-serve-20261104.json`](evidence/measured-cpu-serve-20261104.json). Hardware: cpu-basic / 2 cores / 16G. |
| Energy (CPU lab) | **UNAVAILABLE** | `joules=null`. MEASURED only from a real NVML delta. Never invent a joule. |
| llama.cpp / Ollama | **UNQUALIFIED recipe** | Local command templates; verify downloaded bytes against the artifact pin. No current serving observation. |
| Read-only qualification | **NOT_QUALIFIED for serving** | Identity state and legacy-route retirement are separate; no prompt is sent and metadata cannot establish serving readiness. |
| GPU / vLLM / TGI / TRT-LLM / SGLang / Dynamo | **ROADMAP** | Until MEASURED on named hardware. |
| GPU attention | **ROADMAP** | No fused/paged-attention LIVE claim. No tokens/s invented. |
| Speculative decode (`szl-specdecode`) | **SPECDECODE=UNAVAILABLE** until soft-import LIVE | Optional pointer to [`szl-holdings/szl-specdecode`](https://github.com/szl-holdings/szl-specdecode) / [`SZLHOLDINGS/szl-specdecode`](https://huggingface.co/SZLHOLDINGS/szl-specdecode). Soft-imports `verify_draft` when installed; else honest null. GPU kernel **UNAVAILABLE**. Speedup **null**. Not a Medusa/EAGLE/vLLM rehost. |
| `szl-forge-lab` | **SNAPSHOT** | Not a trainer. Not a serve target. No LIVE URL, curl, or model pin. |
| energy-attested-runs | **8/8 SIMULATED** | Not MEASURED NVML joules. Not a live serve path. Not this recipe's CPU energy evidence. |
| Ask & Act | **not a live control plane** | a11oy operator tab. Does not gate, launch, or control this recipe. |
| Chaski / ReceiptAgent | **ROADMAP** | Same config surface. Not fake LIVE. No pin fabricated. |
| Plan validation | **LIVE** | Outside the weights. Hallucinated `citedNodeIds` → REJECT. Never repaired into a green plan. |
| `brainBinding.status` | **NOT_RESOLVED** | Controller resolves handles outside the weights. |
| Model provenance | **MODEL_PROPOSED** | Real model output. `SYNTHETIC` is fixtures only. |
| Serve receipt | **UNSIGNED** unless a key is present | Hash-chained (request hash, output hash, model pin, energy label). Do not fake DSSE. |
| Λ | **Conjecture 1** | Advisory. Never a theorem. Trust never 100%. |
| Doctrine | v11 LOCKED | 749 / 14 / 163 |
| License | Apache-2.0 | Copyright 2026 SZL Holdings |
| Owner | Stephen P. Lutar Jr. / SZL Holdings | https://a-11-oy.com |

This plate is not proven trust. Verification of a receipt proves integrity of that record, never model quality, safety, or SLA.
