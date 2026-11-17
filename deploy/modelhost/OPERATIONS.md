# Operations: Massed modelhost identity-v2

This runbook covers only `szl-modelhost.service` and the release
`20261116-identity-v2`. It does not authorize changes to other inference engines,
training jobs, SSH, ThinLinc, mesh tunnels, or unrelated systemd overrides.

**The recorded release is operational through SSH:** Gate1 passed full
qualification at **2026-11-16 23:45:38 UTC** and CUDA at
**2026-11-16 23:47:12 UTC**, covering 48 model names and 93 placements. See
section 10 for the verified results. Current status must still be checked;
**public HTTP ingress remains blocked on Cloudflare authorization**. The completed
GET-only audit could not read the target tunnel configuration (401) or Access
organization (403); see [INGRESS.md](INGRESS.md).

Gate1's temporary modelhost pause protected the unrelated Vibe trainer observed
as PID 10095. That trainer exited naturally, and Gate1 was resumed at
**2026-11-16 23:42:10 UTC**, observed as modelhost PID 14459. The pause is historical;
check current process identity and receipts before acting. The later acceptance
records establish the achieved counts; neither a target count nor a start command
would establish them on its own.

## 1. Addresses, paths, and fixed policy

| Item | Gate1 | CUDA |
| --- | --- | --- |
| SSH account/address | `Ubuntu@64.247.196.50` | `Ubuntu@64.247.206.118` |
| HTTP listener | `127.0.0.1:8090` | `127.0.0.1:8091` |
| Original configured names | 49 | 49 |
| Required model placements | 48 | 45 |
| VRAM reserve | 6,000 MiB | 4,000 MiB |
| Free-disk reserve | 50 GiB | 50 GiB |

Both hosts use these paths:

| Purpose | Absolute path |
| --- | --- |
| Release directory | `/home/Ubuntu/szl-modelhost/releases/20261116-identity-v2` |
| Active private configuration | `/home/Ubuntu/szl-modelhost/releases/20261116-identity-v2/host_config.json` |
| Active artifact lock | `/home/Ubuntu/szl-modelhost/releases/20261116-identity-v2/model_lock.json` |
| Runtime Python | `/home/Ubuntu/szl-modelhost/venv/bin/python` |
| Release systemd override | `/etc/systemd/system/szl-modelhost.service.d/70-identity-v2.conf` |
| Runtime receipt | `/home/Ubuntu/szl-modelhost/receipts/latest.json` |
| Release acceptance report | `/home/Ubuntu/szl-modelhost/receipts/acceptance-20261116.json` |
| Documented legacy backups | `/home/Ubuntu/szl-modelhost/releases/20261116-identity-v2/rollback/` |

The original manifest contains one explicitly excluded metadata-only repository,
`khipu-abstain-r3-candidate`. CUDA's lock records three additional capacity
exclusions. Preserve the reasons and the 49-name denominator. Complete assignment
means 48 + 45 = 93 model placements, covering 48 names with weights; replicas are
not additional distinct models. Same-name artifacts can have different pinned
revisions on the two machines.

## 2. Routine inspection and access

Use the authorized operator machine and its existing trusted SSH key. From the
directory containing `fleet_client.py`:

```powershell
python fleet_client.py inventory --host gate1
python fleet_client.py inventory --host cuda
```

The client defaults to `~/.ssh/szl_massed_a6000_ed25519`, loads existing known host
keys, and rejects unknown hosts. Use `--key-file` and `--known-hosts` only to
select existing authorized files. A host-key error needs identity verification;
do not bypass it by accepting an unknown key automatically.

The helper runs a fixed command over SSH, sends JSON on stdin, and calls only
loopback endpoints. It does not follow redirects, use ambient HTTP proxies for
loopback traffic, retry generation, or choose a different host after failure.
Its optional origin credential comes from the active release configuration above.
Keep `origin_auth_token_file` absolute; relative-path interpretation can otherwise
depend on a process's working directory. The credential remains in host memory
and is not printed or placed in a shell command.

Inside the selected host's existing SSH session, inspect the service and resources:

```bash
systemctl show szl-modelhost.service --no-pager \
  -p ActiveState -p SubState -p MainPID -p NRestarts -p FragmentPath -p DropInPaths
nvidia-smi --query-compute-apps=pid,process_name,used_gpu_memory --format=csv,noheader,nounits
nvidia-smi --query-gpu=memory.free,memory.total --format=csv,noheader,nounits
df -B1 /home/Ubuntu/szl-modelhost
ss -ltn '( sport = :8090 or sport = :8091 )'
```

Record protected workloads before and after any lifecycle operation. Preserve
Bonsai, Colibri, Hatun, llama-server, and other services present in the host's
baseline. A newly observed GPU process must be identified and coordinated with
its owner before changing capacity assumptions. Inspect only sanitized process
arguments; command lines and environment dumps may contain credentials.

The configured modelhost listener should be the host's assigned loopback port.
An SSH connection or an active tunnel connector does not prove public-origin
closure. A publicly authenticated hostname is a separate release step with its
own unauthenticated-rejection, authorized-request, and origin-bypass evidence.

## 3. Interpreting health, readiness, and receipts

| Observation | Interpretation |
| --- | --- |
| `/health` returns 200 | The process can answer; inspect initialization and loaded fields separately |
| `/ready` returns 200 with `ready: true` | Required models are loaded, identity-verified, canary-verified and fresh; initialization and resource reserves pass |
| `/ready` returns 503 | Read the explicit reasons and resources; keep that failure visible |
| A generation succeeds | The selected request executed; it does not establish full coverage or resource readiness |
| `latest.json` exists | Check boot ID, timestamp, hashes, and live endpoints; an old receipt can outlive a stopped process |
| Qualifier exit status is 0 | Operational acceptance passed; inspect `readiness_pass` and `fully_ready` separately |

The runtime checks canary freshness against a 24-hour maximum age. Each loaded
adapter receives a one-token boot canary and is eligible for idle refresh every
six hours. A canary records actual generated-token count, output SHA256, duration,
and time. An EOS-only completion can establish execution while producing empty
decoded text; no quality claim follows.

`latest.json` is written atomically every 60 seconds with mode 0600. It records
source/lock SHA256 values, host and boot IDs, all model states, exclusions,
readiness, resources, admission state, and counters. It also retains legacy
heartbeat fields `loaded`, `statuses`, `free_mb`, and `gpu`. Optional Hub upload is
independent at 600-second intervals and is enabled only when configured.

These receipts are unsigned operational observations. Neither source hashes nor
canaries constitute a signed attestation, quality benchmark, energy measurement,
or latency SLA. Receipt writers retain no prompt/output text. The operator
client intentionally prints the generated response.

## 4. Service lifecycle

Operate one host at a time. Verify the selected service, release hashes, current
resource pressure, and protected-workload baseline before making a change. Keep
a current record of the source, lock, configuration location, and systemd
activation state. Never run a second full modelhost alongside the existing one
as a diagnostic: both would allocate GPU memory.

To stop only the modelhost during a coordinated capacity hold:

```bash
sudo systemctl stop szl-modelhost.service
```

Confirm its PID has exited and that protected GPU processes remain unchanged.
Keep receipts from the stopped boot as history; do not present them as fresh
readiness. A stop does not disable unrelated units or terminate another session's
training process.

To resume an already configured release after its capacity hold has cleared:

```bash
sudo systemctl start szl-modelhost.service
```

For a reviewed change to this service's systemd override, reload unit definitions
and restart this one unit:

```bash
sudo systemctl daemon-reload
sudo systemctl restart szl-modelhost.service
```

A configuration or lock update needs a service restart to take effect; it does
not itself require `daemon-reload` if unit definitions did not change. Do not
restart merely because a stale observation is unclear. Inspect the current boot
and recent structured events first:

```bash
journalctl -u szl-modelhost.service --since '15 minutes ago' --no-pager
```

Boot verifies files, loads models, and runs canaries before opening the HTTP
listener. Allow that initialization to complete and observe progress externally.
The qualifier makes one pass after the listener is available; it is not a boot
poller. A growing restart count or repeated load failure requires diagnosis,
not repeated launches.

The runtime's 60-second generation limit is cooperative. A client-side timeout
can occur while the server still executes the request. The gate remains held
until that call exits. Do not retry an ambiguous timed-out request blindly,
especially on another host, or kill an unrelated GPU process to free memory.

## 5. Exact-identity generation

Use a loaded model from the selected host's catalog:

```powershell
python fleet_client.py generate --host cuda --model MODEL_NAME --prompt-file C:\SZL\prompt.txt --max-new-tokens 32
```

For a custom consumer, follow this sequence:

1. Read `/models` on the chosen host and select `models[MODEL_NAME]`.
2. Record its repository, revision, and `artifact_fingerprint`. Confirm its
   loaded/verified state and the readiness policy needed by the caller.
3. Send `model`, `prompt`, `max_new_tokens`, and
   `expected_artifact_fingerprint` in the JSON request.
4. Verify the returned model name and exact fingerprint before accepting the
   output. Retain boot/request IDs and measured usage as needed.

The expected fingerprint is 64 lowercase hexadecimal characters. A malformed
value returns 400; a valid but different identity returns 409 before generation.
The fleet helper performs this fence automatically, but choosing another host
still requires an explicit decision. If a consumer requires the previous
artifact, compare the target host's fingerprint with that previous value rather
than accepting whatever a same-name entry currently points to.

The recorded [fleet comparison](evidence/fleet-catalog-comparison-20261116.json)
found 38 common names with identical fingerprints and seven common names with
different pinned artifacts. Three additional names are available only on Gate1.
This is a point-in-time comparison; refresh it before a later routing decision.

| Failure | Operator response |
| --- | --- |
| 404 `unknown_model` | Select an existing catalog entry; requests do not introduce new models |
| 503 `model_unavailable` | Inspect the lock/status/exclusion; generation will not lazy-load it |
| 409 `artifact_identity_mismatch` | Reconcile the intended artifact with the catalog; do not silently replace the expected fingerprint |
| 400 invalid token count | Use an integer within the configured ceiling; Booleans/floats/strings are rejected |
| 413 body/prompt/input-token limit | Reduce the request; character and token limits are separate |
| 503 `busy`, `queue_timeout`, or `http_workers_busy` | Respect bounded capacity; the current helper does not retry automatically |
| 503 generation OOM or 500 generation failure | Inspect safe event codes and resource pressure; the server marks canary evidence failed and does not reload on demand |
| Readiness 503 with disk/VRAM reserve reason | Restore real capacity within the existing policy; successful inference does not erase the readiness failure |

## 6. Run the acceptance qualifier

The expected runtime files for this release are:

| File | SHA256 |
| --- | --- |
| `szl_modelhost.py` | `df093c548351d85f4b79c36cafa97fb634d3f2b260408fb3a1a59f6b43dfc24f` |
| `contract.py` | `06f433a895ab261f89584213f7b88b23f275d0970ed0a96a35ac6e67739506d6` |

After the listener is available, run this inside each host's SSH session:

```bash
SZL_RELEASE=/home/Ubuntu/szl-modelhost/releases/20261116-identity-v2
SZL_PYTHON=/home/Ubuntu/szl-modelhost/venv/bin/python
"$SZL_PYTHON" "$SZL_RELEASE/qualify_running.py" \
  --config "$SZL_RELEASE/host_config.json" \
  --output /home/Ubuntu/szl-modelhost/receipts/acceptance-20261116.json \
  --expected-source-sha df093c548351d85f4b79c36cafa97fb634d3f2b260408fb3a1a59f6b43dfc24f \
  --expected-contract-sha 06f433a895ab261f89584213f7b88b23f275d0970ed0a96a35ac6e67739506d6
```

Archive an existing acceptance report under its boot/time identity before
replacing it if historical evidence is needed. The configured denominator stays
49; do not override it to the loaded count.

The qualifier checks `/health`, `/models`, and `/ready`, matches source bytes and
the current runtime receipt to the live boot, and verifies all required models'
identity/canary evidence. It then checks unknown-model rejection, Boolean and
excessive token counts, oversized bodies, wrong fingerprints, and excessive
input tokens. Finally it performs one fingerprint-bound request for at most eight
new tokens per distinct required base revision and checks the boot again.

The output contains actual completion tokens, measured duration, output SHA256,
identities, dependency-version observations, and readiness details. It contains
no generated text or prompts. Source, boot, manifest, and model-evidence failures
stop acceptance before those generation probes.

Exit 0 is an operational pass. A report may legitimately show
`operational_pass: true`, `readiness_pass: false`, and `fully_ready: false` because
of disk pressure. Record all three values and the real readiness reasons. Do
not call that host fully ready until its actual reserve checks pass.

## 7. Offline planner and capacity changes

`freeze_cache.py` creates a frozen lock from existing cache contents. It neither
contacts the Hub nor downloads missing models. A reviewed exclusion policy maps
configured names to explicit reasons. Missing artifacts retain visible states.
Stage a candidate lock at a new path, inspect its pins and exclusions, and retain
the previous lock before activation; do not overwrite the active lock casually.

```bash
/home/Ubuntu/szl-modelhost/venv/bin/python \
  /home/Ubuntu/szl-modelhost/releases/20261116-identity-v2/freeze_cache.py \
  --config /home/Ubuntu/szl-modelhost/releases/20261116-identity-v2/host_config.json \
  --cache /home/Ubuntu/szl-modelhost/hf/hub \
  --exclusion-policy /absolute/path/to/reviewed-exclusion-policy.json \
  --output /absolute/path/to/new-candidate-model_lock.json
```

The BF16 planner validates bounded safetensors headers and projects floating
storage to two bytes per element while preserving integer-buffer widths. It
retains five-percent headroom, 256 MiB overhead, a 900 MiB floor, and the existing
per-host reserves. `estimate_base_vram(base_path, files)` returns the estimate and
explanatory `vram_planning` metadata. These fields do not enter artifact
fingerprints; modifying a lock still changes the whole-lock receipt hash and
requires a fresh boot/qualification record.

The observed CUDA correction for `szl-provenance-native-v2-lora` changed its base
estimate from 3,673 to 1,965 MiB because the pinned file contains 852,985,920 F32
elements loaded as BF16. The 4,000 MiB reserve stayed intact. This documented
planning correction is distinct from the subsequent live qualification recorded
in section 10.

Use `deduplicate_cache.py` only with an explicit reviewed immutable-file plan.
It audits by default; application verifies content hashes and file metadata
before replacing a duplicate with a hardlink. Do not remove unique caches,
training artifacts, or unrelated model stores. Each archive
requires its completed manifest and verification receipt before it can support a
separate reviewed restore or cleanup decision.

For this release, the rollout owner recorded eight specific CUDA cache-blob
evictions after source and Gate1 restore-copy hashes had been verified. The
measured reclaimed space was 27,269,738,496 bytes, and verified restore copies
were preserved. This completed operation is not a reusable deletion rule. Consult
its per-blob mapping and verification receipts before any future restore or
cleanup; do not infer that every cache file is covered by one archive.
The exact mappings are in
[cache-restoration-plan-20261116.json](evidence/cache-restoration-plan-20261116.json),
with [restoration steps](evidence/RESTORE.md) and the
[cleanup summary](evidence/cache-cleanup-summary-20261116.md).

## 8. Recovery from documented backups

Read-only inspection confirmed these files in the rollback directory on both
hosts:

| Backup | Meaning |
| --- | --- |
| `activation-before.json` | Recorded pre-activation observations; inspect privately before recovery |
| `szl-modelhost.service` | Legacy service unit, referencing the original source path |
| `szl_modelhost.py` | Legacy source, SHA256 `3442aa272549cd476252b553b1044398140a29de79f317c195e6703d56ba5ddb` |

**There is no `host_config.json` backup in this rollback directory.** The original
private configuration is a separate dependency. Verify its availability and
provenance from the operator's retained records; never reconstruct credentials,
copy another host's configuration, or assume a missing backup exists.

The legacy source binds to `0.0.0.0`. Merely disabling `70-identity-v2.conf` and
restarting can restore that exposure and removes the v2 serving/readiness
contract. This runbook therefore does not provide an unconditional legacy-start
command.

Recovery sequence:

1. Stop only `szl-modelhost.service` if recovery requires changing its active
   files. Preserve current receipts, lock, source hashes, and the exact failed
   release before altering anything.
2. Verify the documented source backup's SHA256 and read the pre-activation
   record. Confirm the backed-up unit and original private configuration belong
   to this host. Do not select a backup by a filename guess or wildcard.
3. Establish and verify how the restored listener will remain confined to the
   intended operator access path before starting legacy code. If that cannot be
   established, leave this service stopped while correcting the v2 release.
4. Restore only the documented files needed for this one service. If reverting
   unit selection, change only its named `70-identity-v2.conf` override; preserve
   every unrelated drop-in and service. Reload systemd only after the reviewed
   unit change.
5. Start only this service when its source, configuration, network exposure, and
   current GPU capacity are verified. Check protected workloads again.
6. Record the actual recovered contract and source identity. Legacy code cannot
   pass this release's v2 qualifier and must not inherit an old v2 acceptance
   report. Requalify the v2 release before claiming v2 readiness again.

A source backup is not a model-cache backup. Do not restore or delete cached
weights from broad cleanup scripts during service recovery.

## 9. Provider API helper

From the authorized operator machine:

```powershell
python massed_inventory.py --key-file C:\SZL\massed_api.key
```

This helper makes one read-only provider inventory request to
`https://vm.massedcompute.com/api/v1/instance` using the selected key. It emits
only allowlisted instance metadata and safe error codes; the provider's raw
response may contain passwords and startup commands and must not be printed or
archived wholesale. It does not enumerate alternative credentials or change
instances. Provider availability, SSH access, and modelhost readiness must be
assessed separately.

## 10. Verified release evidence and remaining work

The rollout owner supplied these final live acceptance observations on
2026-11-16. Both reports have `operational_pass`, `readiness_pass`, and
`fully_ready` set to true, with zero failed checks.

| Evidence | Gate1 | CUDA |
| --- | --- | --- |
| Qualification completed UTC | 23:45:38 | 23:47:12 |
| Configured names | 49 | 49 |
| Required / loaded / verified | 48 / 48 / 48 | 45 / 45 / 45 |
| Acceptance checks | 25 | 23 |
| Representative base groups | 8 | 6 |
| Probe output-token ceiling | 8 | 8 |
| Main PID at observation | 14459 | 2425966 |
| Systemd restart count | 0 | 0 |
| Free GPU memory | 13,311 MiB | 5,279 MiB |
| Free disk bytes | 100,484,075,520 | 54,181,744,640 |
| Listener | `127.0.0.1:8090` | `127.0.0.1:8091` |
| External laptop TCP probe | Public port 8090 timed out | Public port 8091 timed out |

Gate1's protected llama-server PID 958 was unchanged. Gate1 modelhost allocation
was observed at 33,050 MiB. These process IDs describe that observation; use the
current service state before any later lifecycle action.

The host report path is `/home/Ubuntu/szl-modelhost/receipts/acceptance-20261116.json`
on each machine. Repository export names and verified report hashes are:

| Export filename | SHA256 |
| --- | --- |
| `gate1-acceptance-20261116.json` | `0094dbba4a834950b4fbb53bd829f718939ad41fe37d3cad253cf7b02a81a811` |
| `cuda-acceptance-20261116.json` | `c8b0c31f818aa615369c737613ab693c69f6e76ac57ae954220d00377eed4a85` |

The reports carry their boot IDs, running source identities, coverage,
canary-verification results, request evidence, versions, and resource results.
Refer to the corresponding runtime receipt for detailed per-model canaries and
the source and lock hashes. The runtime source and contract
hashes remain those in section 6.

The rollout owner also recorded 87 fixture tests passing locally and in both
host virtual environments, with the existing three-version Python CI green.
Fixture results and live acceptance are separate evidence.

The [scheduled-heartbeat verification](evidence/heartbeat-verification-20261116.json)
at 23:56:02 UTC confirmed both existing Hub publishers. Gate1's natural upload
at 23:55:27.928664 UTC matched its current boot and 48/48/48 coverage; CUDA's
upload at 23:47:22.879359 UTC matched its current boot and 45/45/45 coverage.
Both were ready and matched local source, contract, and lock hashes. No manual
upload or service restart was used for this observation.

CUDA had 494,653,440 bytes, approximately 472 MiB, above the configured
53,687,091,200-byte disk reserve at acceptance. Keep that narrow margin visible
in ongoing monitoring. Do not lower the reserve if usage grows and readiness
later returns 503.

The subsequent verified removal of disabled Snap revision 168 reclaimed
645,160,960 bytes, leaving 54,826,770,432 free bytes (51.06 GiB), or 1.06 GiB above
the reserve. The current revision 177, active container, protected processes,
and Gate1 restoration archives were preserved. The
[final operator inventory](evidence/operator-final-inventory-20261116.json)
then returned exit 0, HTTP 200, and `ready: true` for both hosts. Historical
acceptance files retain their original measurements.

**Public HTTP ingress is not complete.** The GET-only audit ran from protected
main in the existing production environment and recorded `INCOMPLETE`: the target
tunnel configuration returned HTTP 401 / Cloudflare code 1001, and the Access
organization returned HTTP 403 / code 10000. Successful empty inventory lists
do not establish absence. No Cloudflare configuration was changed. Correct the
approved credential's account/resource authorization and rerun the existing
audit as documented in [INGRESS.md](INGRESS.md).

A public hostname still requires a complete Cloudflare application/policy audit,
intended audience validation, rejection of
unauthenticated requests, a successful authorized request, and origin-bypass
verification. Preserve unrelated tunnels. The accepted access path for this
release is SSH to each host's loopback service.
