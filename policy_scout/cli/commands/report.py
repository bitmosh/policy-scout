"""report command handler."""

import json
import sys


def handle_report_command(args):
    """Handle report subcommands."""
    from ...reports.writer import get_report_root
    from ...audit.redaction import redact_string

    report_root = get_report_root()

    # Check if report root exists
    if not report_root.exists():
        print(
            "No Scout Reports found. Run a Policy Scout command with --report, sandbox, or sweep first.",
            file=sys.stderr,
        )
        sys.exit(1)

    if args.report_subcommand == "list":
        # Scan report root for report directories
        reports = []
        for report_dir in sorted(report_root.iterdir(), reverse=True):
            if not report_dir.is_dir():
                continue
            report_id = report_dir.name
            if not report_id.startswith("report_"):
                continue

            # Check for report files
            md_path = report_dir / "report.md"
            json_path = report_dir / "report.json"

            if not (md_path.exists() or json_path.exists()):
                continue

            # Try to read JSON for metadata
            metadata = {
                "report_id": report_id,
                "has_markdown": md_path.exists(),
                "has_json": json_path.exists(),
            }
            if json_path.exists():
                try:
                    with open(json_path, "r") as f:
                        data = json.load(f)
                        metadata["report_type"] = data.get("report_type", "unknown")
                        metadata["title"] = data.get("title", "")
                        metadata["created_at"] = data.get("created_at", "")
                except Exception:
                    pass

            reports.append(metadata)

        # Apply type filter
        if args.type:
            reports = [r for r in reports if r.get("report_type") == args.type]

        # Apply pagination
        total_count = len(reports)
        offset = getattr(args, "offset", 0)
        reports = reports[offset: offset + args.limit]

        if args.json:
            print(json.dumps({"reports": reports, "total_count": total_count, "offset": offset}, indent=2))
        else:
            if not reports:
                print("No Scout Reports found.")
                return
            print("Recent Scout Reports:")
            if args.type:
                print(f"Filtered by type: {args.type}")
            if total_count > len(reports):
                print(
                    f"Showing {len(reports)} reports (offset {offset}, total: {total_count})"
                )
            print()
            for report in reports:
                print(f"Report ID: {report['report_id']}")
                print(f"Type: {report.get('report_type', 'unknown')}")
                print(f"Title: {report.get('title', 'N/A')}")
                created_at = report.get("created_at", "")
                print(f"Created: {created_at if created_at else 'unknown'}")
                print(
                    f"Formats: Markdown={report['has_markdown']}, JSON={report['has_json']}"
                )
                print()
            print("Use: policy-scout report show <report_id>")

    elif args.report_subcommand == "show":
        report_dir = report_root / args.report_id
        if not report_dir.exists():
            print(f"Error: Report not found: {args.report_id}", file=sys.stderr)
            sys.exit(1)

        md_path = report_dir / "report.md"
        json_path = report_dir / "report.json"

        if args.json:
            # Show JSON report
            if not json_path.exists():
                print(
                    f"Error: JSON report not found for {args.report_id}",
                    file=sys.stderr,
                )
                sys.exit(1)
            with open(json_path, "r") as f:
                content = f.read()
                # Apply redaction on read
                content = redact_string(content)
                print(content)
        else:
            # Show Markdown report
            if not md_path.exists():
                if json_path.exists():
                    # Fallback to JSON summary
                    print("Markdown report not found. Showing JSON summary:")
                    with open(json_path, "r") as f:
                        data = json.load(f)
                        print(f"Report ID: {data.get('report_id')}")
                        print(f"Type: {data.get('report_type')}")
                        print(f"Title: {data.get('title')}")
                        print(f"Summary: {data.get('summary')}")
                        print(f"Created: {data.get('created_at')}")
                else:
                    print(
                        f"Error: No report files found for {args.report_id}",
                        file=sys.stderr,
                    )
                    sys.exit(1)
            else:
                with open(md_path, "r") as f:
                    content = f.read()
                    # Apply redaction on read
                    content = redact_string(content)
                    print(content)

    elif args.report_subcommand == "export":
        report_dir = report_root / args.report_id
        if not report_dir.exists():
            print(f"Error: Report not found: {args.report_id}", file=sys.stderr)
            sys.exit(1)

        if args.format == "markdown":
            md_path = report_dir / "report.md"
            if not md_path.exists():
                print(
                    f"Error: Markdown report not found for {args.report_id}",
                    file=sys.stderr,
                )
                sys.exit(1)
            with open(md_path, "r") as f:
                content = f.read()
                # Apply redaction on read
                content = redact_string(content)
                print(content)
        elif args.format == "json":
            json_path = report_dir / "report.json"
            if not json_path.exists():
                print(
                    f"Error: JSON report not found for {args.report_id}",
                    file=sys.stderr,
                )
                sys.exit(1)
            with open(json_path, "r") as f:
                content = f.read()
                # Apply redaction on read
                content = redact_string(content)
                print(content)

    else:
        print("Error: No report subcommand provided", file=sys.stderr)
        sys.exit(1)
