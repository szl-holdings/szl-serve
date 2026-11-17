# Public HTTPS ingress: authorization blocker and acceptance evidence

**Status: blocked on Cloudflare account/resource authorization.** The modelhost
release is available through its documented SSH access path. Public HTTPS
ingress has not been accepted. The completed configuration audit could not read
the existing target tunnel configuration or the Access organization, so it
cannot establish the current modelhost hostname, origin mapping, Access team,
audience, or effective policies.

This document records the observed blocker and the next reviewable action.
Current runtime operation and SSH access are covered in [OPERATIONS.md](OPERATIONS.md).

## Observed audit

| Evidence | Recorded value |
| --- | --- |
| Audit implementation PR | [szl-holdings/a11oy#3579](https://github.com/szl-holdings/a11oy/pull/3579) |
| Protected-main source | [6848d7a1f15fe72883cc49bf3172e0e4439a325a](https://github.com/szl-holdings/a11oy/commit/6848d7a1f15fe72883cc49bf3172e0e4439a325a) |
| Workflow | [Audit Massed Cloudflare Ingress](https://github.com/szl-holdings/a11oy/blob/6848d7a1f15fe72883cc49bf3172e0e4439a325a/.github/workflows/audit-massed-cloudflare-ingress.yml) |
| Execution | [Run 43983235206, attempt 1](https://github.com/szl-holdings/a11oy/actions/runs/43983235206) |
| Event and environment | `workflow_dispatch`, `main`, existing `production` environment |
| Observation time | `2026-11-16T23:55:01.957828+00:00` |
| Audit result | `INCOMPLETE`; workflow failed to preserve that incomplete result |
| Provider requests | Five GET requests; zero provider mutations |
| Sanitized artifact | `massed-cloudflare-ingress-43983235206-1`, artifact ID `14283772433` |
| Saved evidence | [cloudflare-ingress-audit-20261116.json](evidence/cloudflare-ingress-audit-20261116.json) |
| Evidence SHA256 | `2db93abdc6e2e8462e742f734f3451e2bb413c7443d230beb0f05a8ce89053c8` |

The run source was exactly the merged revision above. Its network-free contract
job passed all 21 tests before the provider-read job ran. The normal PR merge
also passed the exact required lockfile check and audit contract. Neither
branch protection nor the existing production environment guards were changed.

The fixed audit scope is:

| Resource | Identifier |
| --- | --- |
| Cloudflare account | `d2d4084c615189c795286ea5eaec2229` |
| Existing CUDA tunnel | `acd44edd-1faf-46fc-ad40-c2977b3f98fb` |

The sanitized report records these results:

| Read | Result | Established fact |
| --- | --- | --- |
| Target tunnel configuration | HTTP `401`, Cloudflare code `1001`, `PERMISSION_DENIED` | This credential could not read the target configuration |
| Access organization | HTTP `403`, Cloudflare code `10000`, `PERMISSION_DENIED` | This credential could not read the organization/team configuration |
| Tunnel inventory | Successful empty page | No tunnel was visible in that response |
| Access application inventory | Successful empty page | No application was visible in that response |
| Service-token metadata inventory | Successful empty page | No service-token metadata was visible in that response |
| Application policies | Zero requests | No relevant application was visible for policy inspection |

**Empty lists are not proof of absence.** Cloudflare documents that
[resource-scoped Access roles return only permitted resources](https://developers.cloudflare.com/changelog/product/access/).
The known existing connector must therefore not be treated as missing because
this credential received an empty inventory. The audit does not distinguish a
missing read capability from an account/resource authorization mismatch.

The evidence is an unsigned operational observation:
`signature: UNSIGNED`, `security_verdict: NOT_EVALUATED`, and
`provider_mutations: false`. No CI credential or raw provider response was
retrieved into this repository.

## Next action: correct the approved read authorization

An authorized Cloudflare account administrator must verify that the approved
credential context covers the account and target tunnel above, together with
the relevant Access resources. Make any correction through the established
secret-management process for the existing GitHub `production` environment and
its `CLOUDFLARE_API_TOKEN` binding. Coordinate the scope with that credential's
existing consumers.

The documented read capabilities for the fixed audit are:

| Read capability | Official endpoint documentation |
| --- | --- |
| `Cloudflare Tunnel Read`, or the documented equivalent `Cloudflare One Connector: cloudflared Read` | [Get Tunnel configuration](https://developers.cloudflare.com/api/resources/zero_trust/subresources/tunnels/subresources/cloudflared/subresources/configurations/methods/get/) |
| `Access: Apps and Policies Read` | [List Access applications](https://developers.cloudflare.com/api/resources/zero_trust/subresources/access/subresources/applications/methods/list/) |
| `Access: Service Tokens Read` | [List service tokens](https://developers.cloudflare.com/api/resources/zero_trust/subresources/access/subresources/service_tokens/methods/list/) |
| `Access: Organizations, Identity Providers, and Groups Read` | [Get your Zero Trust organization](https://developers.cloudflare.com/api/resources/zero_trust/subresources/organizations/methods/list/) |

Permission names alone are insufficient: the authorized account and resource
scopes must include the resources being inspected. Keep credentials within the
approved environment. Do not put token values, service-token client secrets,
authorization headers, or credentials in chat, logs, commits, or artifacts.

The audit remains fixed-scope and GET-only. Correcting its authorization does
not authorize creating or changing tunnels, DNS routes, Access applications,
policies, service tokens, or connector settings.

### Normal rerun after authorization is corrected

Use the existing authorized GitHub CLI identity:

```powershell
gh workflow run audit-massed-cloudflare-ingress.yml --repo szl-holdings/a11oy --ref main
```

The already merged workflow has no dispatch inputs. Honor the existing
production environment gates. Record the returned run URL and verify that its
protected-main source contains merge
`6848d7a1f15fe72883cc49bf3172e0e4439a325a`; any later change to the audit itself
needs its normal review and checks.

Retrieve only the resulting
`massed-cloudflare-ingress-RUN_ID-RUN_ATTEMPT` sanitized artifact. Preserve this
failed observation as history, and record the new source revision, timestamp,
run/attempt, report hash, and result. An `OBSERVED` report establishes completed
configuration reads; public HTTPS still requires the acceptance evidence below.
An `INCOMPLETE` or `BLOCKED` report remains a blocker.

## Evidence required before accepting public HTTPS

1. **Observed configuration and a reviewed mapping.** Read the target tunnel's
   actual configuration, its existing hostnames and origins, the Access team
   domain, relevant application IDs/audiences, and effective policy decisions.
   Establish the intended modelhost hostname-to-origin mapping from those
   observations. Preserve existing routes and record any separately approved
   change and rollback before applying it.

2. **Authentication enforcement.** Prove that the intended HTTPS hostname
   rejects requests with missing or invalid identity, without executing model
   generation. Prove the intended machine client can authenticate using the
   approved service identity. Record effective policy scope and origin-side
   validation so another route cannot bypass that policy. Cloudflare documents
   [service-token authentication](https://developers.cloudflare.com/cloudflare-one/access-controls/service-credentials/service-tokens/)
   and [connector Access validation parameters](https://developers.cloudflare.com/tunnel/reference/origin-parameters/).
   An edge application alone does not establish that every origin path is protected.

3. **No direct-origin bypass.** Confirm the assigned listeners remain
   `127.0.0.1:8090` on Gate1 and `127.0.0.1:8091` on CUDA. From an external
   vantage point, prove the public IP/port paths cannot return model data or
   execute inference outside the approved authentication path. Preserve SSH
   access and compare the observed bindings with the active service configuration.

4. **Authorized end-to-end execution.** Validate TLS hostname/certificate
   verification, health, readiness, and the model catalog through the intended
   HTTPS endpoint. Run a bounded, fingerprint-bound canary and compare its
   selected host, model fingerprint, boot identity, and result with the current
   SSH/loopback evidence. Prove wrong-fingerprint rejection still occurs before
   generation. Same-name models with different fingerprints are not interchangeable.

5. **Failure behavior and capacity.** Preserve explicit readiness, admission,
   identity, and timeout failures through the HTTPS path. Establish client,
   edge, connector, and origin timeout behavior without automatic duplicate
   generation or silent failover to a different artifact.

6. **Preservation and fresh receipts.** Record before/after checks for existing
   connector routes, ThinLinc, SSH, Bonsai on port 8080, and other protected
   workloads. Retain sanitized configuration, negative-authentication,
   origin-bypass, authorized-canary, and regression evidence with timestamps
   and source/runtime identities. Credentials and prompt/output text do not
   belong in shared acceptance artifacts.

The completed audit did not restart, replace, or reconfigure any connector.
The existing CUDA `szl-massed-cloudflared.service`, laptop mesh routes,
ThinLinc, SSH, Bonsai, and unrelated origins were preserved. Public HTTPS
acceptance remains pending the authorization correction and the evidence above.
