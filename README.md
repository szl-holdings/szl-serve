# szl-serve

**One OpenAI-shaped chat call. One pinned weight. One receipt.**

KERNEL-owned canonical governed-inference **recipe + validator + energy receipt** for SZL Holdings.

This is **not** a vendor engine. It is the silhouette of 2026 serving (vLLM / SGLang / TGI / TensorRT-LLM / llama.cpp / Dynamo) — without copying those engines, and without fabricating tokens/s or joules.

Homepage: [a-11-oy.com](https://a-11-oy.com) · Owner: Stephen P. Lutar Jr. / SZL Holdings · Doctrine v11 LOCKED **749/14/163** · Λ = **Conjecture 1** (advisory, never a theorem) · Apache-2.0

---

## What this is NOT

- **Not vLLM. Not TGI. Not TensorRT-LLM. Not SGLang. Not Dynamo.** Those names are the 2026 silhouette. This repo does not vendor-copy them. GPU path is **ROADMAP** until MEASURED on named hardware.
- **Not a tokens/s leaderboard.** A MEASURED sample is raw completion tokens + `elapsed_ms`. No derived tok/s rating.
- **Not proven trust.** A hash-chained receipt proves integrity of that record. It does not prove the model, the lab, or Λ.
- **Not a takeover of the Hugging Face Space.** FORGE owns [`szl-holdings/szl-forge`](https://github.com/szl-holdings/szl-forge) / [`SZLHOLDINGS/szl-model-inference-lab`](https://huggingface.co/spaces/SZLHOLDINGS/szl-model-inference-lab). This KERNEL repo **pins** that MEASURED lab as the live CPU path. It does not invent a second runtime.

Honesty plate: [`CARD.md`](CARD.md).

---

## LIVE CPU (MEASURED) — pin this lab, do not invent a second runtime

| | |
|---|---|
| Surface | https://szlholdings-szl-model-inference-lab.hf.space |
| Space | https://huggingface.co/spaces/SZLHOLDINGS/szl-model-inference-lab |
| FORGE source | https://github.com/szl-holdings/szl-forge/tree/main/spaces/szl-model-inference-lab |
| API | OpenAI subset `POST /v1/chat/completions` |
| Model | `SZLHOLDINGS/SZL-Khipu-1.5B-GGUF@67d60ec577730747055491640cfb91fc4a4b5d25` |
| GGUF | `SZL-Khipu-1.5B-Q4_K_M.gguf` · SHA-256 `13c1a1993063e1dff92f7413ccf48eaca6d48efc8801ae9af35961ae3396623a` · 986047904 bytes |
| Sample 2026-08-28 | **21** completion tokens · **elapsed_ms 2053** · execution_record **UNSIGNED** |
| Energy | `joules=null` · label **UNAVAILABLE** (CPU lab; MEASURED only from a real NVML delta) |
| SLA | Best-effort public demo. No provider SLA. Dummy bearer `not-a-secret` only — never a real token. |

```bash
curl https://szlholdings-szl-model-inference-lab.hf.space/v1/chat/completions \
  -H "content-type: application/json" \
  -H "authorization: Bearer not-a-secret" \
  -d '{"model":"SZLHOLDINGS/SZL-Khipu-1.5B-GGUF@67d60ec577730747055491640cfb91fc4a4b5d25","messages":[{"role":"user","content":"Explain one limit of cryptographic receipts."}],"max_tokens":24,"stream":false}'
```

Contract: `/.well-known/szl-inference-contract.json`. Identity: `/api/v1/identity`.

---

## Airgap twin — same pin, local llama.cpp / Ollama

Local llama.cpp and Ollama run the **same** Q4_K_M bytes. They are the airgap twin of the Space, **not** a clone of vLLM.

```bash
llama-cli    -hf SZLHOLDINGS/SZL-Khipu-1.5B-GGUF:Q4_K_M
llama-server -hf SZLHOLDINGS/SZL-Khipu-1.5B-GGUF:Q4_K_M
ollama run hf.co/SZLHOLDINGS/SZL-Khipu-1.5B-GGUF:Q4_K_M
```

Print the recipe (no GGUF download):

```bash
python -m szl_serve recipe
```

---

## Controller — schema outside the weights

Model output is **proposal-only**. Copy of [`khipu.schema.json`](schemas/khipu.schema.json) is pinned from the GGUF repo (SHA-256 `b95f9927366dae7c5d36cfb7de6e229eb605524318ab642a6aa2292a212170d0`).

- Hallucinated `citedNodeIds` → **REJECT**. Never silently repaired into a green plan.
- `brainBinding.status` stays **NOT_RESOLVED**.
- Real model output provenance is **MODEL_PROPOSED**, not `SYNTHETIC`.
- Invalid JSON / cross-field contract failure → fail closed (`REJECT`).

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
| FORGE Space CPU OpenAI subset + GGUF pin + 2026-08-28 sample | **MEASURED** |
| llama.cpp / Ollama commands for the same pin | **LIVE recipe** (airgap twin) |
| Energy on CPU | **UNAVAILABLE** |
| GPU / vLLM / TGI / TensorRT-LLM / SGLang / Dynamo | **ROADMAP** |
| GPU attention | **ROADMAP** — no fused/paged-attention LIVE claim; no tokens/s invented |
| Chaski, ReceiptAgent weights | **ROADMAP** stubs on this config surface — not fake LIVE |

Λ is Conjecture 1. It does not become a theorem because a chat call returned 21 tokens.

---

## Tests

Unit tests use fixture plan JSON. **No network. Do not download the ~1 GB GGUF in CI.**

```bash
pip install -e ".[test]"
pytest -q
```

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

[a-11-oy.com](https://a-11-oy.com) · [Khipu GGUF](https://huggingface.co/SZLHOLDINGS/SZL-Khipu-1.5B-GGUF) · [MEASURED lab (FORGE)](https://huggingface.co/spaces/SZLHOLDINGS/szl-model-inference-lab)

<sub>SLSA: L1 honest · L2 attested · L3 roadmap. Λ = Conjecture 1. Trust ceiling 0.97 — never 100%.</sub>

</div>
