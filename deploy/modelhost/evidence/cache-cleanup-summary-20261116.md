# CUDA cache retention and disk recovery - 2026-11-16

## Measured result

After the final approved cleanup at 2026-11-16T23:52:09Z, CUDA had **54,826,770,432 bytes (51.061 GiB) available**. The unchanged reserve is 53,687,091,200 bytes (50 GiB), leaving 1,139,679,232 bytes (1.061 GiB) above the readiness floor.

The reviewed operation receipts report **37,755,154,432 bytes (35.162 GiB)** of aggregate measured gains. This total sums each operation's own before/after measurement; concurrent small filesystem writes can make it differ slightly from a single long-interval disk comparison.

| Operation | Measured gain, bytes |
|---|---:|
| Immutable cache hardlink consolidation | 4,074,954,752 |
| Reproducible package and image cleanup | 5,765,300,224 |
| Eight reviewed physical model-cache blobs | 27,269,738,496 |
| Disabled Snap revision 168 and exact derived cache link | 645,160,960 |

## Evidence provenance

- **Immutable cache hardlink consolidation:** CUDA receipt /home/Ubuntu/szl-modelhost/releases/20261116-identity-v2/dedup-receipt.json; SHA-256 a36e826d4229714735110a14b48a6d54aba8d11a81b4cf5130b09402a4145402.

- **Reproducible package and image cleanup:** CUDA receipt /home/Ubuntu/szl-modelhost/ops-receipts/20261116-cache-cleanup/receipt.json; SHA-256 13443948a34134664907634c3dd1debc56a1e676c706eaf4cf489fe0e1b81eff.

- **Eight reviewed physical model-cache blobs:** CUDA receipt /home/Ubuntu/szl-modelhost/ops-receipts/20261116-model-cache-eviction/receipt.json; SHA-256 56abdc6f3a3d66524377dbfcc49f6a78bf82312c84d4fbc51aaebb9da6ce62ad.

- **Disabled Snap revision 168 and exact derived cache link:** CUDA receipt /home/Ubuntu/szl-modelhost/ops-receipts/20261116-disabled-snap-168/receipt.json; SHA-256 21ac084fb614e741c2fcc3c221479e643cd6d2b3dc63bc59fbbd4f45bbe5e739.

## Scope and retained data

The eight-entry reviewed plan and eviction receipt are copied verbatim as cache-restoration-plan-20261116.json and cache-eviction-20261116.json. Every source and restoration blob was freshly hashed before eviction. Current frozen model/base physical files and process FD/mmap references were checked again before each unlink. Model snapshot aliases, metadata, adapters, base files, and all Gate1 archives were preserved.

Four unused merged full weights are retained through verified immutable hardlinks in Gate1's cuda-merged-weights-20261116 archive. Four Qwen2.5-7B-Instruct shards are retained in a dedicated Gate1 cache at revision a09a35458c702b33eeacc393d103063234e8bc28, with exact CUDA-source SHA-256 matches. The original small-cache files, directories, and symlinks are retained in source-cache-metadata.tar. The combined preservation records cover the complete original 78-entry cache inventory.

The additional Snap action removed only disabled gnome-46-2404 revision 168 through Snap and then its one confirmed derived cache hardlink. Revision 177 and its image identity were preserved. Its receipt is cache-disabled-snap-cleanup-20261116.json.

## Workload continuity

The reviewed eviction and subsequent Snap cleanup preserved the same process identities for qwen36 PID 1047 and llama-server PIDs 2139629 and 2307902. The protected CUDA Docker container 74e0e38a2f3b remained running on image 0131784115794405cb36a8068a82d7aea0937196d1d6e844b9dd021252ccf7e4. Cache operations performed no service start, stop, or restart, and made no Gate1 archive changes during eviction or Snap cleanup.

Root resumed Gate1's modelhost at 2026-11-16 23:42:10 UTC. Current acceptance and operator CLI readiness evidence is maintained separately in the existing evidence files.

## Restoration

See RESTORE.md and the reviewed eight-entry plan for exact source and Gate1 restoration paths, byte counts, SHA-256 values, ownership, modes, and timestamps. Restore through a verified adjacent temporary file and atomic rename; existing model-cache aliases will resolve again.

## Content review

The copied JSON evidence was checked for credential-bearing fields, private-key material, and common credential patterns before writing. Only these reviewed receipts, the restoration plan, and this summary were copied. No raw Docker environment/configuration inspection was copied.
