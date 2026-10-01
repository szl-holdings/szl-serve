# Ollama publication kit — SZL-Khipu-1.5B

Publishes the existing public GGUF bytes of `SZLHOLDINGS/SZL-Khipu-1.5B-GGUF` (Hub revision
`d9731f1d586c7f615790163a759dc0f14872b523`) to the Ollama library as `szlholdings/szl-khipu-1.5b`
with tags `q4_k_m` (default), `q5_k_m`, `q8_0`. Nothing is re-quantized; every file is SHA-256
verified against the Hub card before `ollama create`.

| Tag | File | SHA-256 (Hub LFS OID) | Bytes |
|---|---|---|---|
| `q4_k_m` (latest) | SZL-Khipu-1.5B-Q4_K_M.gguf | `13c1a1993063e1dff92f7413ccf48eaca6d48efc8801ae9af35961ae3396623a` | 986,047,904 |
| `q5_k_m` | SZL-Khipu-1.5B-Q5_K_M.gguf | `3bf460ac163c5dc952c273999c38a41349e3e6d666e4b713aed22c996860fd4c` | 1,125,049,760 |
| `q8_0` | SZL-Khipu-1.5B-Q8_0.gguf | `6aff1087f64631679f4cdf032613aee6911dbde38cd3bac6b81bf63741a56f0d` | 1,646,572,448 |

## Files

- `Modelfile.szl-khipu-1.5b.{q4_k_m,q5_k_m,q8_0}` — `FROM` the verified GGUF; `TEMPLATE` byte-identical to the Ollama library `qwen2.5` template (blob `eb4402837c78`); `temperature 0`, `num_ctx 8192`, ChatML stops; Apache-2.0 notice. No `SYSTEM` is baked in: the documented contract is a user-turn JSON object and an external controller validates the plan against `khipu.schema.json`.
- `Publish-Ollama.ps1` — Windows PowerShell 5.1 (Administrator) runbook: preflight (ollama present, key present, namespace exists, disk) → download + verify → create → smoke at temperature 0 → push → public read-back → receipt JSON in `%USERPROFILE%\szl-ollama\receipts\`. Stops before any push if a gate fails.
- `OLLAMA_PAGE.md` — text for the model page README on ollama.com (the push does not carry a README; paste it once).

## Owner steps that cannot be automated

1. Create the `szlholdings` account at https://ollama.com/signup (the namespace was unclaimed on 2026-10-01).
2. Add the local Ollama public key (`%USERPROFILE%\.ollama\id_ed25519.pub`, printed by the runbook) at https://ollama.com/settings/keys.
3. Run `Publish-Ollama.ps1`. 4. Paste `OLLAMA_PAGE.md` into the model page.

## Not published, on purpose

`SZLHOLDINGS/A11OY-MINI` stays Hub-only. Its card states `publication_eligible=false` and
`autonomy_eligible=false`; a library listing would contradict the artifact's own gate.
Revisit only after that card changes through the model-publish gate, not here.

## Claims boundary

`ollama run hf.co/SZLHOLDINGS/SZL-Khipu-1.5B-GGUF:Q4_K_M` already works; this kit adds a library
listing and short name, not a new model. The smoke step is a single temperature-0 prompt recorded
in the receipt; it is not an evaluation. The signed receipts on the Hub cover the pre-quantized
checkpoint, not GGUF numerics. Λ = Conjecture 1.
