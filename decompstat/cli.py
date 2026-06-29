"""Command line interface for DecompStat."""

from __future__ import annotations

import argparse
import sys

from .io import read_dataset
from .schema import SchemaError, dump_metadata_template
from .validate import validate_dataset, summarize_inventory
from .compare import paired_comparison, mutant_scan
from .ranking import rank_stability, rank_agreement
from .report import write_report, file_sha256


def _add_common_io(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("data", help="Canonical DecompStat CSV file")
    parser.add_argument("metadata", help="Metadata sidecar JSON/YAML")


def cmd_template(args: argparse.Namespace) -> int:
    dump_metadata_template(args.out)
    return 0


def cmd_validate(args: argparse.Namespace) -> int:
    df, meta = read_dataset(args.data, args.metadata)
    validate_dataset(df, meta, require_snapshot_assertion=args.require_snapshot_assertion)
    print("Validation OK")
    print(f"rows={len(df)} samples={df['sample_id'].nunique()} methods={df['method_id'].nunique()}")
    return 0


def cmd_summarize(args: argparse.Namespace) -> int:
    df, meta = read_dataset(args.data, args.metadata)
    table = summarize_inventory(df)
    write_report(
        table,
        args.out,
        title="DecompStat inventory summary",
        provenance={"input_sha256": file_sha256(args.data)},
    )
    return 0


def cmd_compare(args: argparse.Namespace) -> int:
    df, meta = read_dataset(args.data, args.metadata)
    table, coverage = paired_comparison(
        df,
        meta,
        ref=args.ref,
        target=args.target,
        n_boot=args.n_boot,
        seed=args.seed,
    )
    provenance = {
        "input_sha256": file_sha256(args.data),
        "ref": args.ref,
        "target": args.target,
        **{k: str(v) for k, v in coverage.items()},
    }
    write_report(table, args.out, title="DecompStat paired comparison", provenance=provenance)
    return 0


def cmd_mutant_scan(args: argparse.Namespace) -> int:
    df, meta = read_dataset(args.data, args.metadata)
    table, coverage = mutant_scan(
        df,
        meta,
        method_id=args.method,
        wt_state=args.wt,
        mutant_state=args.mut,
        n_boot=args.n_boot,
        seed=args.seed,
    )
    provenance = {
        "input_sha256": file_sha256(args.data),
        "method": args.method,
        "wt": args.wt,
        "mut": args.mut,
        **{k: str(v) for k, v in coverage.items()},
    }
    write_report(table, args.out, title="DecompStat mutant scan", provenance=provenance)
    return 0


def cmd_rank_stability(args: argparse.Namespace) -> int:
    df, meta = read_dataset(args.data, args.metadata)
    table = rank_stability(
        df,
        meta,
        group=args.group,
        top_k=args.top_k,
        n_boot=args.n_boot,
        seed=args.seed,
    )
    write_report(
        table,
        args.out,
        title="DecompStat rank stability",
        provenance={"input_sha256": file_sha256(args.data), "group": args.group},
    )
    return 0


def cmd_rank_agreement(args: argparse.Namespace) -> int:
    import pandas as pd

    df, meta = read_dataset(args.data, args.metadata)
    result = rank_agreement(df, meta, args.group_a, args.group_b, top_k=args.top_k)
    table = pd.DataFrame([result])
    write_report(
        table,
        args.out,
        title="DecompStat rank agreement",
        provenance={"input_sha256": file_sha256(args.data), "group_a": args.group_a, "group_b": args.group_b},
    )
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="decompstat",
        description="Paired comparison and rank-stability analysis of residue-pair energy decompositions.",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    p = sub.add_parser("metadata-template", help="Write a metadata sidecar template")
    p.add_argument("out", help="Output .yaml/.yml/.json path")
    p.set_defaults(func=cmd_template)

    p = sub.add_parser("validate", help="Validate canonical data and metadata")
    _add_common_io(p)
    p.add_argument("--require-snapshot-assertion", action="store_true")
    p.set_defaults(func=cmd_validate)

    p = sub.add_parser("summarize", help="Write inventory summary")
    _add_common_io(p)
    p.add_argument("--out", required=True, help="Output .csv/.json/.md")
    p.set_defaults(func=cmd_summarize)

    p = sub.add_parser("compare", help="Paired comparison of two selected groups")
    _add_common_io(p)
    p.add_argument("--ref", required=True, help="Selector, e.g. state_id=WT,method_id=MM_MM")
    p.add_argument("--target", required=True, help="Selector, e.g. state_id=WT,method_id=SQM_MM")
    p.add_argument("--out", required=True, help="Output .csv/.json/.md")
    p.add_argument("--n-boot", type=int, default=1000)
    p.add_argument("--seed", type=int, default=12345)
    p.set_defaults(func=cmd_compare)

    p = sub.add_parser("mutant-scan", help="WT-vs-mutant paired comparison for one method")
    _add_common_io(p)
    p.add_argument("--method", required=True, help="method_id to compare")
    p.add_argument("--wt", required=True, help="WT state_id")
    p.add_argument("--mut", required=True, help="mutant state_id")
    p.add_argument("--out", required=True, help="Output .csv/.json/.md")
    p.add_argument("--n-boot", type=int, default=1000)
    p.add_argument("--seed", type=int, default=12345)
    p.set_defaults(func=cmd_mutant_scan)

    p = sub.add_parser("rank-stability", help="Bootstrap rank stability for one selected group")
    _add_common_io(p)
    p.add_argument("--group", required=True, help="Selector, e.g. state_id=WT,method_id=SQM_MM")
    p.add_argument("--top-k", type=int, default=10)
    p.add_argument("--out", required=True, help="Output .csv/.json/.md")
    p.add_argument("--n-boot", type=int, default=1000)
    p.add_argument("--seed", type=int, default=12345)
    p.set_defaults(func=cmd_rank_stability)

    p = sub.add_parser("rank-agreement", help="Spearman/top-k Jaccard agreement between groups")
    _add_common_io(p)
    p.add_argument("--group-a", required=True)
    p.add_argument("--group-b", required=True)
    p.add_argument("--top-k", type=int, default=10)
    p.add_argument("--out", required=True, help="Output .csv/.json/.md")
    p.set_defaults(func=cmd_rank_agreement)

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        return int(args.func(args))
    except (SchemaError, ValueError, FileNotFoundError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
