# Vendored Fossic

This directory contains the Fossic Rust core and `fossic-py` Python binding used
by Policy Scout.

- Upstream repository: `https://github.com/bitmosh/fossic`
- Upstream commit: `968c2c7e3561ec645133d3667113eb9cffb79000`
- Upstream version: `1.8.1`
- Vendored on: `2026-06-30`
- License: `MIT OR Apache-2.0`

The workspace is intentionally reduced to the crates needed to build the Python
binding: the Fossic Rust core, `fossic-similarity-hnsw`, and `fossic-py`. Its
Cargo lockfile was regenerated for that reduced workspace.

Policy Scout CI builds the binding directly from `vendor/fossic/fossic-py`.
There is no Policy Scout packaging dependency on the upstream Git repository.

To refresh the vendor copy, replace these sources from a known upstream commit,
update the commit/version above, and run the Fossic binding tests plus the full
Policy Scout suite.

