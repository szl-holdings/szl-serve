# CUDA modelhost readiness recovery — November 17, 2026

**Scope: measured, operator-authorized Massed RTX A6000 fleet recovery.**
This is a dated capacity and inference witness, **not** a public HTTPS
gateway acceptance, model-quality certification, system uptime guarantee,
or instruction to remove more data.

## Recovery and preserved serving

At **23:39 UTC**, the existing, source-pinned SSH fleet client read
Gate1 `/ready` as **200/true** with 48/48 identity-verified required
placements. CUDA `/models` returned 200 with 45/45 verified required
placements and four intentional exclusions, but `/ready` returned
**503** for `disk_below_reserve`. The disk admission floor remained
**53,687,091,200 bytes (50 GiB)**.

The authorized operations repair inspected exact old generated worktrees
before making any change: Git ignored outputs, reproducible lockfiles,
inode and modification timestamps, process cwd/fd/arguments, mount
status, and the active `szl-modelhost.service` PID. Only these
reproducible, no-longer-used items were removed on CUDA:

| Exact dated generated output | Measured filesystem gain |
| --- | ---: |
| `szl-platform-963-zod-20261025/node_modules` | 688,107,520 bytes |
| `szl-platform-964-audit/node_modules` | 135,249,920 bytes |
| `szl-linux-verify-20261024/edge-extract` | 705,576,960 bytes |
| **Total measured gains** | **1,528,934,400 bytes** |

Do not substitute apparent `du` sizes for the actual measured free-space
change: shared filesystem objects and hardlinks make the two differ.
The generated JavaScript dependencies can be reinstalled from their
retained `pnpm-lock.yaml` files; the downloaded browser archive in
`edge-dl` was retained. Tracked source, Git history, model weights,
training checkpoints, Docker's active container, installed Snap images,
logs, security controls, and receipts were **not** removed. No running
service was restarted or changed.

At **23:56:18 UTC**, CUDA free disk was **54,284,816,384 bytes**;
fresh `GET /ready` changed from **503** to **200, `ready: true`**,
with 45/45 verified required placements and no reported reasons. The
modelhost boot identity remained consistent. This is only
**597,725,184 bytes (~570 MiB)** above the unchanged 50 GiB floor:
disk growth can revoke readiness again. No proposed operational change
may lower or ignore that reserve to achieve an apparent green status.

## Actual inference measured over the existing governed operator path

The source-pinned `deploy/modelhost/fleet_client.py` at
`szl-serve@f8c2d8ea54c35b69ff88d8ded9b0ef25402bf2e4` was used
through existing known-host-verifying SSH to the **loopback-only** Gate1
and CUDA listeners. It never uploads SSH keys or exposes a public GPU
origin. Both hosts confirmed their model catalogs and ready states.

An existing loaded `salad-a11oy-mini-r1` model answered one bounded
eight-token-maximum neutral inference per host. The client required
the catalog's exact 64-character artifact fingerprint and checked the
generation response identity:

| Host | Current `/ready` | Required verified placements | Tiny canary |
| --- | --- | ---: | --- |
| Gate1 | HTTP 200 / true | 48/48 | HTTP 200, 2 completion tokens, 225.372 ms |
| CUDA | HTTP 200 / true | 45/45 | HTTP 200, 2 completion tokens, 193.421 ms |

Both catalogs reported the same fingerprint for that **specific**
`salad-a11oy-mini-r1` alias, not universal model parity across hosts.
These values are single observations, **not** token/s benchmarks,
capability evaluations, availability targets, or evidence of distributed
tensor-parallel inference. The fleet has **93 model placements across
48 distinct model names** at its previously reviewed assignment; it
is not 93 distinct models.

Private source-bound receipts remain on the authorized operator
workstation. Their SHA-256 values are non-signing integrity references:

- Before recovery, fleet readback:
  `73ecd47cd013885c4a1cd2a1e06ec23e4899d2356cc4dbd89386ea5de17b028d`
- Exact generated-output preflight:
  `8720f258438ac56159a6a96605a74f49be67accc4f8c6b4fe6f26cfef7c1c854`
- First two exact cache effects:
  `7f77bf50158c9bafca1edc2f8729d74428f4807b45f168fdd1d1af455b1784c6`,
  `d5a9c2600ae4ed0eee906f4a9289623e6d40490578245b04127243a74c762a83`
- Browser extraction recovery and readiness:
  `e0d38b25724047f4a6076d08456b2896b5065453fb5149e2709971dc54e7fd06`
- Two-host exact-alias canary:
  `c97dda57373c2557fff6eaa2126dffec620a031fbd4f29fb3a2018b9134e4ac9`

## A11oy cloud gateway remains a separate HOLD

At **2026-11-18 00:02 UTC**, the deployed A11oy HF-origin public
sovereign-health endpoint returned HTTP 200 but **`wired: false`**.
It also reported `state: UNKNOWN`; one service-health sample timed
out and another exploratory frontier path returned 404. The publicly
reported build revision was
`87cffe4f61b064c0f794bd9a27e279dc3506b058` at that sample.
The Space configuration *names* for legacy sovereign URLs and key are
present, but their current values were not read, and this cannot prove
they bind to either authorized GPU node.

The opt-in governed A11oy router configuration names
`SZL_ROUTER_BASE_URL`, `SZL_ROUTER_MODEL`,
`SZL_ROUTER_SOURCE_REVISION`, and the `SZL_ROUTER_TOKEN` secret
were not present in the authorized HF Space configuration-name
readback at **23:59 UTC**. Neither runtime success inside Gate1/CUDA
nor the existence of legacy variables can manufacture a safely
authenticated, source-fenced network path from the HF application.

**Admission sequence**, owned by the existing publisher and gateway
rather than a new daemon or exposed raw GPU port:

1. Recover the existing Cloudflare production audit's read authorization
   to the *existing* tunnel and Access organization; its 2026-11-16
   read returned 401/403. Use the existing source-controlled
   `a11oy/.github/workflows/audit-massed-cloudflare-ingress.yml`.
2. Review actual tunnel origin, hostnames, Access application and service
   identity. Prove missing/incorrect identity is rejected **at the edge
   and origin**, and no direct-origin bypass exists. Preserve loopback
   listeners, SSH, ThinLinc, Bonsai and active CUDA workloads.
3. Use the separately pinned `szl-router` source and A11oy's existing
   opt-in governed adapter; ensure PUBLIC/INTERNAL classification,
   exact model alias/fingerprint and source revision, and no recursive
   A11oy routing. Do not move an SSH private key or a raw modelhost URL
   into an HF Space variable.
4. Publish source through its **sole approved** GitHub→Hub writer only
   after normal protected checks and environment approvals. Provision
   the reviewed URL and token via authorized secret management, without
   logging secret values.
5. Test `/api/source`, `/readyz/inference`, a bounded authorized
   generation with exact fingerprint, denial/timeout cases, source
   revision before/after, and public product readback. Keep HTTP 402
   monetization, settlement, DSSE proof, and load/soak separate.

**Current disposition:** GPU *operator serving* **MEASURED/READY** at
the exact sample. A11oy's public cloud-to-GPU inference wiring,
Cloudflare authorization, model quality, signed receipts, and paid
settlement remain **HOLD/UNVERIFIED**. No extra training or public
load testing was launched.
