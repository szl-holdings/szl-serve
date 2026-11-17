# Massed modelhost: identity-v2 release

This directory contains the Transformers/PEFT modelhost, its offline artifact
planner, operator clients, and acceptance checks for the two Massed GPU hosts.
The active release directory is
`/home/Ubuntu/szl-modelhost/releases/20261116-identity-v2`.

**Both hosts passed full operational and readiness qualification:** Gate1 at
**2026-11-16 23:45:38 UTC** and CUDA at **2026-11-16 23:47:12 UTC**. The verified
SSH service covers 48 model names across 93 placements. These are timestamped
acceptance observations; use current receipts and endpoints for ongoing status.
**Public HTTP ingress remains blocked on Cloudflare authorization.** The
completed GET-only audit could not read the target tunnel configuration (401)
or Access organization (403) with the existing production credential. See
[INGRESS.md](INGRESS.md) for the exact observations and next action. See
[OPERATIONS.md](OPERATIONS.md) for evidence, lifecycle, qualification, and recovery.

Gate1 was temporarily paused to preserve an unrelated Vibe training job, observed
as PID 10095. That job exited naturally; the rollout owner resumed the Gate1
modelhost at **2026-11-16 23:42:10 UTC**, observed as PID 14459. These are historical
observations, not permanent process identities. The acceptance records below
follow that resume.

## Host assignments and coverage

| Host | SSH destination | Modelhost listener | Required model placements | VRAM reserve |
| --- | --- | --- | ---: | ---: |
| Gate1 | `Ubuntu@64.247.196.50` | `127.0.0.1:8090` | 48 | 6,000 MiB |
| CUDA | `Ubuntu@64.247.206.118` | `127.0.0.1:8091` | 45 | 4,000 MiB |

Both locks retain all **49 originally configured names**. The
`khipu-abstain-r3-candidate` entry is an explicit metadata-only repository
exclusion, with no model weights at the reviewed revision. CUDA's three
additional capacity exclusions are `salad-frontier-v4-r1`,
`salad-frontier-v5-r1`, and `salad-flagship54-v1`; all three are served by Gate1.
Required coverage is thus
48 placements on Gate1 and 45 on CUDA: **93 assigned placements, achieved at the
recorded acceptance and covering 48 distinct model names with weights**. Placements include replicas; they are
not 93 distinct models. Equal names across hosts also do not guarantee equal
artifact revisions or fingerprints.

The final live catalog comparison found 45 names present on both hosts: 38 had
the same exact artifact fingerprint and seven had different pinned artifacts.
The three Gate1-only names are the CUDA capacity exclusions above. See the
[catalog comparison](evidence/fleet-catalog-comparison-20261116.json); consumers
must keep their expected fingerprint when selecting another host.

The free-disk reserve remains **50 GiB on each host**. Exclusions, missing files,
load failures, and resource pressure remain visible. Do not remove a name from
the denominator or lower a reserve to turn a failing readiness result into a
passing one.

## Exact artifact identity

`freeze_cache.py` reads an existing cache without contacting the Hub. It selects
one exact adapter release/checkpoint directory and records immutable repository
revisions, file sizes, and actual SHA256 hashes. The server verifies the pinned
base files once per loaded base and adapter files before loading. It also checks
that the adapter configuration names the locked base repository.

A base is shared only for the same `repo@revision`; adapter aliases incorporate
the name and fingerprint. Loading uses exact local paths with local-only
options. No request triggers a download or lazy model load.

The artifact fingerprint covers adapter repository/revision, the selected
adapter-config path, adapter file identities, and base repository/revision/file
identities. Local paths and VRAM planning metadata do not enter the fingerprint.
A change to the lock file still changes its separate whole-file SHA256 receipt.

### BF16 allocation planning

The planner reads a safetensors header capped at 16 MiB, validates tensor shapes,
dtypes, offsets, complete file bounds, and stable metadata, and projects floating
tensors to two bytes per element for the runtime's BF16 load. Integer and Boolean
buffers retain their stored widths. It reads no tensor payload for this estimate
and imports no GPU libraries.

The allocation policy remains `max(900 MiB, ceil(projected MiB × 1.05) + 256 MiB)`.
The host's VRAM reserve is added separately and remains unchanged. This corrects
F32-on-disk overestimation; it does not claim exact future allocation or reduce
headroom. The additional `vram_planning` metadata explains the estimate.

## Serving contract

| Endpoint | Contract |
| --- | --- |
| `GET /health` | Process liveness, boot ID, initialization status, and resident models; a 200 does not assert readiness |
| `GET /ready` or `/readyz` | 200 only when required coverage, verified identities, fresh canaries, initialization, and resource reserves all pass; otherwise 503 with reasons |
| `GET /models` | `szl.modelhost/v2` catalog with a `models` object, full manifest, explicit exclusions, identities, canaries, and failures |
| `POST /generate` | Bounded generation using an already loaded model and optional exact-identity fence |

Generation requires `model` and `prompt`. `max_new_tokens` defaults to 256 and
must be an integer within the configured limit. For an exact artifact request,
read the selected host's catalog and send its 64-character lowercase SHA256 as
`expected_artifact_fingerprint`. A mismatch returns **409
`artifact_identity_mismatch` before generation**. Verify the response fingerprint
as well. Responses also carry repository/revision, boot ID, request ID, measured
completion tokens, and elapsed milliseconds.

Defaults are 64 KiB bodies, 16,384 prompt characters, 2,048 input tokens, 256 new
tokens, one active generation, two queued requests, eight HTTP workers, a
2-second queue wait, and a 10-second socket timeout. The Transformers generation
limit is cooperative at 60 seconds. The admission gate remains occupied until
the call exits; the server does not launch overlapping GPU work when a client
wait expires.

Generation can succeed while `/ready` reports a resource problem. Record that
503 and its reasons; successful inference does not override readiness.

## SSH operator access

The supported operator path is encrypted SSH to the selected host and HTTP on
that host's loopback interface. A public authenticated hostname is a separate,
unverified deployment surface. Preserve existing ThinLinc, mesh, SSH, and other
unrelated routes.

From this directory on the authorized operator machine:

```powershell
python fleet_client.py inventory --host cuda
python fleet_client.py generate --host cuda --model MODEL_NAME --prompt-file C:\SZL\prompt.txt --max-new-tokens 32
```

Replace `MODEL_NAME` with a loaded name from that host's catalog. Use
`--host gate1` for Gate1; the client's default is Gate1. The existing default key
is `~/.ssh/szl_massed_a6000_ed25519`. `--key-file` and `--known-hosts` can select
existing trusted files. Unknown SSH host keys are rejected.

The client sends prompts as JSON on SSH stdin, uses fixed host/endpoint
allowlists, disables HTTP proxies and redirects for loopback requests, pins the
catalog fingerprint, and checks the response identity. It makes no automatic
generation retry or cross-host failover. The operator command prints generated
text; the server's operational receipts do not retain that text.

Optional origin authentication is read privately from
`/home/Ubuntu/szl-modelhost/releases/20261116-identity-v2/host_config.json`, the same
active configuration used by the service. Use an absolute
`origin_auth_token_file` path if enabling that option. Do not put credentials in
CLI arguments or commit live configuration.

## Receipts and qualification

Loaded adapters receive a one-token boot canary. Its evidence is operational
execution only: actual completion-token count, output hash, elapsed time, and
UTC timestamp. Idle refresh runs every six hours; evidence older than 24 hours
fails freshness. A failed canary does not silently mark an unloaded or unverified
model as ready.

On each host, local runtime receipts are atomically replaced every 60 seconds at
`/home/Ubuntu/szl-modelhost/receipts/latest.json`, mode 0600. Optional Hub upload
runs independently every 600 seconds. Receipts include source and lock hashes,
boot identity, complete coverage, resource observations, admission state, and
counters. Legacy heartbeat fields `loaded`, `statuses`, `free_mb`, and `gpu`
remain available. These records are unsigned observations and assess no model
quality, correctness, or energy efficiency.

Both naturally scheduled Hub uploads were verified against their current local
boot, source/lock hashes, and ready model counts on 2026-11-16. See the
[heartbeat verification](evidence/heartbeat-verification-20261116.json). No manual
upload was used to substitute for the scheduled publisher.

`qualify_running.py` checks the live boot, the on-disk and running-source hashes,
all required identities and fresh canaries, six negative request cases, and one
real eight-token request per distinct required base revision. It saves only
output hashes, counts, timings, and identities. Use the exact invocation in
[OPERATIONS.md](OPERATIONS.md), producing
`/home/Ubuntu/szl-modelhost/receipts/acceptance-20261116.json` on each host.

**Qualifier exit 0 means `operational_pass`, not full readiness.** Inspect
`readiness_pass`, `fully_ready`, and the actual `/ready` HTTP status and reasons.
A disk-pressure 503 must remain a 503 in acceptance evidence.

## Tools in this directory

| Tool | Purpose and limits |
| --- | --- |
| `szl_modelhost.py` | Versioned loopback serving, identity checks, bounded admission, canaries, and receipts |
| `contract.py` | Pure-stdlib selection, request validation, readiness, and concurrency contracts |
| `freeze_cache.py` | Offline lock creation and BF16 allocation planning from existing cache files |
| `fleet_client.py` | Explicit-host SSH inventory and fingerprint-fenced generation |
| `qualify_running.py` | One-pass acceptance of an already running host; no service controls or model loading |
| `massed_inventory.py` | Read-only provider inventory using one authorized key; outputs only allowlisted fields |
| `deduplicate_cache.py` | Audit or apply an explicit immutable-file hardlink plan after content verification |

The Massed API helper calls `GET
https://vm.massedcompute.com/api/v1/instance`, takes `--key-file` (default
`C:\SZL\massed_api.key`), and strips provider passwords/startup commands from its
output. Provider inventory does not prove SSH reachability or inference
readiness. It does not create, stop, or delete instances.

## Local verification and release evidence

From this directory:

```bash
python -m unittest discover -s . -p 'test_*.py' -q
```

Fixtures cover artifact selection and mutation, BF16 projection, admission and
HTTP bounds, identity fences, exclusions, stale/failed canaries, receipts,
clients, and qualification. The rollout owner recorded **87 tests passing
locally and in both host virtual environments**, with the existing three-version
Python CI green. These tests are separate from the live acceptance below.

| Host | Accepted UTC on 2026-11-16 | Required / loaded / verified | Checks | Representative base groups | Result |
| --- | --- | --- | ---: | ---: | --- |
| Gate1 | 23:45:38 | 48 / 48 / 48 | 25 | 8 | Operational, readiness, and fully-ready flags true |
| CUDA | 23:47:12 | 45 / 45 / 45 | 23 | 6 | Operational, readiness, and fully-ready flags true |

Both runs had zero failed checks. Generation probes were capped at eight new
tokens and were fenced to the catalog artifact. The receipt exports are named
`gate1-acceptance-20261116.json` and `cuda-acceptance-20261116.json`; their SHA256
values and resource observations are recorded in [OPERATIONS.md](OPERATIONS.md).
The reports are available as [Gate1 acceptance](evidence/gate1-acceptance-20261116.json)
and [CUDA acceptance](evidence/cuda-acceptance-20261116.json).

At acceptance, Gate1 had 100,484,075,520 free disk bytes and 13,311 MiB free VRAM;
CUDA had 54,181,744,640 free disk bytes and 5,279 MiB free VRAM. CUDA's disk margin
was only 494,653,440 bytes, approximately 472 MiB above the unchanged 50 GiB
reserve. Continue monitoring that reserve. Both listeners were loopback-only,
and external laptop TCP probes to their public HTTP ports timed out. This does
not complete the separate public-hostname/Cloudflare authentication audit.

A later verified cleanup of disabled Snap revision 168 reclaimed another
645,160,960 bytes. CUDA then had **54,826,770,432 free bytes (51.06 GiB)**,
1.06 GiB above the reserve. The final [operator inventory](evidence/operator-final-inventory-20261116.json)
returned HTTP 200 and `ready: true` on both hosts after that cleanup. The
[cache cleanup summary](evidence/cache-cleanup-summary-20261116.md) and
[restoration instructions](evidence/RESTORE.md) preserve the reviewed scope.
