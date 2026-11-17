# Reviewed model-cache restoration

The cache-eviction-20261116.json receipt and cache-restoration-plan-20261116.json name the eight removed CUDA physical blobs and their verified Gate1 restoration paths.

1. Select the entry by exact source_path; obtain its bytes from archive_path on Gate1 over the existing trusted SSH connection.
2. Write an adjacent temporary file on CUDA. Verify its exact size and SHA-256 against the entry before replacing the physical blob path.
3. Restore the recorded uid, gid, permission mode, and mtime; atomically rename the verified temporary file to source_path.
4. Existing snapshot and blob aliases were preserved and will resolve again after that physical path is restored.

For Qwen, the complete original small-cache metadata is also preserved in /home/Ubuntu/szl-modelhost/cold-cache-archives/cuda-qwen25-7b-20261116/source-cache-metadata.tar, with its manifest and verification receipts in the same directory.

No service was started, stopped, or restarted by these cache operations. Root resumed Gate1's modelhost at 2026-11-16 23:42:10 UTC; this cache work did not change its service state.

Do not restore or remove any additional cache entry based on this receipt.
