# Honesty plate — szl-serve
# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 SZL Holdings · Stephen P. Lutar Jr.

**KERNEL-owned canonical serve recipe + validator + energy receipt.**
Not a vendor engine. Not a takeover of the Hugging Face Space.

| Axis | Label | Fact |
|---|---|---|
| ATELIER serve studio | **LOCKED** | `SZLHOLDINGS/szl-model-inference-lab` **only**. Do not point `szl-serve` at forge-lab. |
| Live CPU runtime | **MEASURED** | Existing lab `https://szlholdings-szl-model-inference-lab.hf.space` — FORGE owns the Space (`szl-holdings/szl-forge`). This repo pins it. Do not invent a second runtime. |
| OpenAI subset | **MEASURED** | `POST /v1/chat/completions` · model `SZLHOLDINGS/SZL-Khipu-1.5B-GGUF@67d60ec577730747055491640cfb91fc4a4b5d25` |
| Weight pin | **MEASURED** | `SZL-Khipu-1.5B-Q4_K_M.gguf` · LFS SHA-256 `13c1a1993063e1dff92f7413ccf48eaca6d48efc8801ae9af35961ae3396623a` · 986047904 bytes |
| Sample 2026-08-28 | **MEASURED** | 21 completion tokens · `elapsed_ms` 2053 · execution_record **UNSIGNED**. Not a tokens/s rating. |
| Energy (CPU lab) | **UNAVAILABLE** | `joules=null`. MEASURED only from a real NVML delta. Never invent a joule. |
| llama.cpp / Ollama | **LIVE recipe** | Airgap twin of the same pin. Not a clone of vLLM. |
| GPU / vLLM / TGI / TRT-LLM / SGLang / Dynamo | **ROADMAP** | Until MEASURED on named hardware. |
| GPU attention | **ROADMAP** | No fused/paged-attention LIVE claim. No tokens/s invented. |
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
