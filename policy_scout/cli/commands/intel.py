# SPDX-License-Identifier: Apache-2.0
"""intel command handler."""

import json
import sys


def handle_intel_command(args) -> None:
    """Handle intel status/clear-cache/evict-expired subcommands."""
    sub = getattr(args, "intel_subcommand", None)

    if sub == "status":
        from ...intel.remote.cache import IntelCache
        from pathlib import Path as _Path

        cache = IntelCache()
        stats = cache.stats()

        data_dir = _Path(__file__).parent.parent.parent / "data"
        npm_meta_path = data_dir / "top_npm_packages.yaml"
        pypi_meta_path = data_dir / "top_pypi_packages.yaml"
        kb_path = data_dir / "known_bad_registry.yaml"

        def _read_generated_at(p: _Path) -> str:
            if not p.exists():
                return "missing"
            for line in p.read_text().splitlines()[:5]:
                if "generated_at:" in line:
                    return line.split("generated_at:")[-1].strip()
            return "unknown"

        status = {
            "local_adapters": {
                "typosquatting": "ok",
                "known_bad": "ok" if kb_path.exists() else "missing",
                "lockfile_integrity": "ok",
            },
            "data_files": {
                "top_npm_packages": {
                    "status": "ok" if npm_meta_path.exists() else "missing",
                    "generated_at": _read_generated_at(npm_meta_path),
                },
                "top_pypi_packages": {
                    "status": "ok" if pypi_meta_path.exists() else "missing",
                    "generated_at": _read_generated_at(pypi_meta_path),
                },
                "known_bad_registry": {
                    "status": "ok" if kb_path.exists() else "missing",
                    "generated_at": _read_generated_at(kb_path),
                },
            },
            "remote_cache": stats,
            "remote_adapters": "disabled (use --with-intel to enable)",
        }

        if getattr(args, "json", False):
            print(json.dumps(status, indent=2))
        else:
            print("Intel Status")
            print("=" * 40)
            print("Local adapters:")
            for name, st in status["local_adapters"].items():
                mark = "✓" if st == "ok" else "✗"
                print(f"  {mark} {name}: {st}")
            print("Data files:")
            for name, info in status["data_files"].items():
                mark = "✓" if info["status"] == "ok" else "✗"
                print(f"  {mark} {name} (generated: {info['generated_at']})")
            print(f"Remote cache: {stats['live_entries']} live / {stats['total_entries']} total entries")

    elif sub == "clear-cache":
        from ...intel.remote.cache import IntelCache
        n = IntelCache().clear()
        print(f"Cleared {n} cache entries.")

    elif sub == "evict-expired":
        from ...intel.remote.cache import IntelCache
        n = IntelCache().evict_expired()
        print(f"Evicted {n} expired cache entries.")

    else:
        print("Error: No intel subcommand provided (status|clear-cache|evict-expired)", file=sys.stderr)
        sys.exit(1)
