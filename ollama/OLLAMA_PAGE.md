# szlholdings/szl-khipu-1.5b

Governed, grounded-only navigator for the SZL receipt lake. A QLoRA fine-tune of Qwen2.5-1.5B-Instruct that reads a JSON list of evidence handles and answers with a JSON plan: NAVIGATE citing offered handles, or ABSTAIN with a reason. Proposal-only. It never executes anything.

```
ollama run szlholdings/szl-khipu-1.5b
```

Tags: `q4_k_m` (default, 0.99 GB), `q5_k_m` (1.13 GB), `q8_0` (1.65 GB). Temperature 0, context 8192, Qwen2.5 ChatML template.

## Prompt contract

The user turn is one JSON object. Candidates are handles only, never node content.

```json
{"query": "Which handle records the rolling 24h spend-cap policy?",
 "candidates": [{"nodeId": "node://khipu-synthetic/0000000000000000", "nodeKind": "CLAIM", "label": "DECLARED", "note": "synthetic handle - topic tag policy-spend-cap; no node content."}]}
```

Expected output is one JSON plan per `khipu.schema.json`:

```json
{"contentAccess": "HANDLES_ONLY", "brainBinding": {"status": "NOT_RESOLVED"}, "decision": "NAVIGATE", "citedNodeIds": ["node://khipu-synthetic/0000000000000000"], "abstainReason": null}
```

Validate every plan against the schema, the offered candidates and your policy before acting on it.

## Provenance

- Bytes: identical to `hf.co/SZLHOLDINGS/SZL-Khipu-1.5B-GGUF` at revision `d9731f1d586c7f615790163a759dc0f14872b523`. SHA-256 per file is on the Hub card and was re-verified before this push.
- Base: Qwen/Qwen2.5-1.5B-Instruct, Apache-2.0. Fine-tune: SZLHOLDINGS/SZL-Khipu-1.5B, Apache-2.0.
- Owner-signed training and evaluation receipts travel with the full-precision checkpoint on the Hub (Ed25519 over canonical JSON). They cover the pre-quantized checkpoint, not these GGUF files. No post-quantization benchmark is claimed.

## What this is not

Not a signed checkpoint. Not an action executor. Not an independently evaluated model. Λ stays Conjecture 1.

Source: github.com/szl-holdings/szl-serve (recipe) and github.com/szl-holdings/szl-forge (training harness). Product: a-11-oy.com. Proof origin: a11oy.net.
