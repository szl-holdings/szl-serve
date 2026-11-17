# Migrating the retired public CPU recipe

`POST /v1/chat/completions` at the public model inference lab is **RETIRED**
(HTTP 410). `szl-serve recipe` prints navigation and historical evidence;
`live_openai_curl()` raises `RetiredRecipeError`. No old request is forwarded,
retried against another route, or converted into an inference call.

The lab declares `/api/v3/governed-infer` as its upstream successor. That is a
different governed protocol, not an OpenAI chat alias. Use the existing A11oy
Atelier boundary described here, which owns authentication, validation,
governance, and receipt persistence. This package adds no execution client.

## Open the existing form

Open `/command-centre#cpu-work` on your verified, operator-managed A11oy
deployment. Confirm that the deployed form/API supports this contract; the
recipe does not probe or claim that a particular deployment is ready.

Authenticate as an operator, review the specific prompt, and explicitly
acknowledge its disclosure to the public CPU lab. Submit only the prompt you
have reviewed. The form sends no inference merely because you navigate to it.
Do not put secrets, credentials, personal data, or other sensitive content in
this public prompt. The operator credential is for A11oy only.

## Existing authenticated API contract

The following is a contract example, not an executable command. Supply the
operator credential only to your verified A11oy origin, never to the public
lab or a provider-supplied successor URL.

```http
POST /api/a11oy/v1/atelier/cpu-lab/turn
Authorization: Bearer <A11OY_OPERATOR_TOKEN>
Content-Type: application/json
```

Only after acknowledging public disclosure of the specific prompt, submit:

```json
{
  "prompt": "<the public prompt you reviewed>",
  "declared": "PUBLIC",
  "public_share_acknowledged": true,
  "max_output_tokens": 24
}
```

`public_share_acknowledged` must be the JSON boolean `true`; it is not a default
or a replacement for operator review. `declared` must be `PUBLIC`, and the
output limit must not exceed 32 tokens. A dummy bearer does not authenticate
this route. No real credential is included in this documentation.

Grounding is required. The model can propose text; it has no tool or action
authority. A response is not permission to act. The deterministic A11oy backend
keeps its policy, validation, signature, and ledger boundaries. A failed or
incomplete outcome must not be reclassified as completed by a caller.

For a validated successful completion, the response contract includes:

```json
{
  "provider_decision": "PROPOSAL",
  "authority": "NO_ACTION_AUTHORITY",
  "executed": false,
  "provider_output_signature_status": "UNSIGNED_LOCAL"
}
```

These are expected success fields, not a response observed by this recipe or a
claim of current deployment readiness. `UNSIGNED_LOCAL` is the provider output's
signature status; it does not claim an independent signature on that output.

## Interpret read-only qualification correctly

`szl-serve qualify` reads only `/api/build-info`, `/api/v1/identity`,
`/.well-known/szl-inference-contract.json`, and `/v1/models`. It does not invoke
either generation route, follow the declared successor, or send a credential.

The receipt's existing `state` describes pinned identity checks. Its independent
`legacy_route` section reports retirement, conflicting declarations, unknown
metadata, or an observed declaration. Even a top-level metadata `READY` does
not override a retired route. A failed build/models read cannot erase retirement
already observed in identity or contract. Missing source attribution stays
unknown; a Space URL is not proof of a source repository.

`serving_ready` remains `false` and `serving_state` remains `NOT_QUALIFIED`.
Those fields and route observations are included in the receipt hash. CLI exit
2 means retired/conflicting route declarations. Exit 1 means unknown/divergent
identity checks or incomplete/unknown route declarations. Exit 0 requires
observed pinned identity fields and complete, consistent, nonretired route
declarations. Exit zero still does not qualify serving.

The 2026-11-04 CPU sample, old Forge source pin, and exact Khipu artifact hashes
remain historical evidence. Their preservation does not certify the current
public runtime. The dated `frontier/model-wave-routing-2026-09-08.json` snapshot
also retains its historical baseline `LIVE` label. It identifies an artifact,
not a current public endpoint or serving qualification. Its default remains
`HOLD`, production promotion remains disabled, and the route planner returns
non-executable proposals. The snapshot is not rewritten as current evidence.

The separately deployed `deploy/modelhost/` service retains its own readiness
gates and is outside this migration. Λ remains Conjecture 1; model output never
becomes authorization.
