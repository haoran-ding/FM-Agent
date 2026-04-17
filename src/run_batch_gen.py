"""Show batch plan, verify spec coverage, and identify missing specs for retry."""

import argparse
import json
import sys
from pathlib import Path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Show batch plan or verify spec coverage for a phase."
    )
    parser.add_argument("--phase", type=int, required=True, help="Phase number")
    parser.add_argument(
        "--verify-only",
        action="store_true",
        help="Only print summary and exit 1 if any functions are missing specs",
    )
    parser.add_argument(
        "--missing-files",
        action="store_true",
        help="Print only the list of function files that are missing specs (one per line), exit 1 if any",
    )
    parser.add_argument(
        "--verify-layer",
        type=int,
        default=None,
        metavar="L",
        help="Restrict verification to a specific layer index",
    )
    parser.add_argument(
        "--batch-dir",
        default=None,
        help="Override batch prompts directory (default: auto from phases.json)",
    )
    return parser.parse_args()


def _has_spec(filepath: Path) -> bool:
    """Check whether the first line of *filepath* contains '[SPEC]'."""
    try:
        with open(filepath, "r", errors="replace") as f:
            first_line = f.readline()
        return "[SPEC]" in first_line
    except OSError:
        return False


def main() -> int:
    args = parse_args()

    # work_dir is the fm_agent/ directory (parent of spec_prompts/ where this script lives)
    work_dir = Path(__file__).resolve().parent.parent
    # repo_root is the project root (parent of fm_agent/)
    repo_root = work_dir.parent

    if args.batch_dir:
        batch_dir = Path(args.batch_dir)
    else:
        phases_path = work_dir / "phases.json"
        with open(phases_path) as f:
            phases_json = json.load(f)
        project = phases_json["project"]
        batch_dir = (
            work_dir
            / "spec_prompts"
            / f"batch_prompts_{project}_phase{args.phase:02d}"
        )

    manifest_path = batch_dir / "manifest.json"
    if not manifest_path.exists():
        print(f"manifest not found: {manifest_path}", file=sys.stderr)
        return 1

    with open(manifest_path) as f:
        manifest = json.load(f)

    batches = manifest.get("batches", [])
    total = 0
    specced = 0
    missing: list[str] = []

    show_plan = not args.verify_only and not args.missing_files

    if show_plan:
        print(
            f"Phase {manifest['phase']}  |  "
            f"{manifest['total_functions']} functions  |  "
            f"{manifest['total_batches']} batches"
        )
        print()

    for batch in batches:
        if args.verify_layer is not None and batch.get("layer") != args.verify_layer:
            continue

        functions = batch.get("functions", [])
        statuses: list[tuple[str, bool]] = []
        for func_file in functions:
            done = _has_spec(repo_root / func_file)
            statuses.append((func_file, done))
            total += 1
            if done:
                specced += 1
            else:
                missing.append(func_file)

        if show_plan:
            tag = "cycle" if batch.get("is_cycle") else "layer"
            print(
                f"Batch {batch['index']:>3d}  "
                f"({tag} {batch['layer']}, {batch['num_functions']} fn)"
            )
            for func_file, done in statuses:
                mark = "\u2713" if done else "\u25CB"
                print(f"  {mark} {func_file}")
            print()

    if args.verify_layer is not None and total == 0:
        print(
            f"No functions found for layer {args.verify_layer} in manifest. "
            f"Was generate_batch_prompts.py run with --layers that includes {args.verify_layer}?",
            file=sys.stderr,
        )
        return 1

    if args.missing_files:
        for m in missing:
            print(m)
        return 1 if missing else 0

    # Summary
    if args.verify_only:
        layer_label = f" (layer {args.verify_layer})" if args.verify_layer is not None else ""
        print(f"{specced}/{total} specced{layer_label}")
        if missing:
            print(f"\nMissing specs ({len(missing)}):")
            for m in missing:
                print(f"  - {m}")
            return 1
        return 0

    # In show-plan mode, also print a brief summary line
    print(f"--- {specced}/{total} specced ---")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
