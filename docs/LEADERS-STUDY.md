# Domain Leader Study — szl-serve (canonical governed serve recipe)

OUROBOROS phase-3, cohort-02 tranche-2, Kimi ruling W26-C2T2-KIMI-20261123-ASK (GO, 7 bindings). PROPOSE-ONLY, DRAFT. Documentation only, no implementation in this PR.

## Current state (repo inspection 2026-11-23)
Python repo; description: canonical SZL governed serve recipe: llama.cpp/Ollama CPU honest path for Khipu GGUF, schema validation outside. Topics: apache-2.0, governed-ai, inference, llama-cpp, ollama, python.

## Domain leaders studied
| Leader | What they have | Key sources |
| --- | --- | --- |
| llama.cpp quantize tooling (ggml-org) | The canonical GGUF quantization documentation: per-format precision tradeoffs (k-quants, etc.) written in-repo next to the tool that does it — the honesty standard this repo already leans on | raw.githubusercontent.com/ggml-org/llama.cpp/master/tools/quantize/README.md (accessed 2026-11-23) |
| JSON Schema + Ajv | The reference contract for validating serving I/O outside the hot path: schema-first, generation-supported validation with precise error paths | ajv.js.org/json-schema.html (accessed 2026-11-23) |

## What the leaders do better
- llama.cpp documents quantization cost/quality tradeoffs per format in the same repo as the code, so a serving recipe citing q-format can be checked directly against upstream truth.
- Ajv-class validation reports exactly which keyword and instance path failed — the leader version of fail-closed: reject with attribution, never a bare 400.

## Gaps
- Recipe is description-measured as schema-validation-outside, but no documented per-format quant choice receipt (which GGUF format, why, measured perplexity or task delta) was found in card scope.
- No documented error-attribution contract for schema rejections on the serve surface.

## Ranked #1 absorb proposal (NOT implemented in this PR)
Document a quant-choice receipt per served GGUF (format, upstream doc citation, measured quality note) and an Ajv-class error-attribution contract for rejections (keyword + instance path, never bare). Expected benefit: honest-path CPU serve becomes externally auditable end-to-end; rejection behavior becomes receipt-able. Cost/risk: low; docs-contract only. Validation: one serve run emitting both receipts. Rollback: contract removal only.

## Sources
- llama.cpp quantize README: https://github.com/ggml-org/llama.cpp/blob/master/tools/quantize/README.md (accessed 2026-11-23)
- Ajv JSON Schema docs: https://ajv.js.org/json-schema.html (accessed 2026-11-23)
