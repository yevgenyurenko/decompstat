"""Deterministic report writers."""

from __future__ import annotations

from pathlib import Path
import json
import hashlib

import pandas as pd

from . import __version__


def file_sha256(path: str | Path) -> str:
    p = Path(path)
    h = hashlib.sha256()
    with p.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def _markdown_table(df: pd.DataFrame) -> str:
    if df.empty:
        return "_No rows._"
    cols = [str(c) for c in df.columns]
    rows = []
    rows.append("| " + " | ".join(cols) + " |")
    rows.append("| " + " | ".join(["---"] * len(cols)) + " |")
    for _, row in df.iterrows():
        vals = []
        for c in df.columns:
            val = row[c]
            if isinstance(val, float):
                vals.append(f"{val:.6g}")
            else:
                vals.append(str(val))
        rows.append("| " + " | ".join(vals) + " |")
    return "\n".join(rows)


def write_report(
    table: pd.DataFrame,
    out: str | Path,
    *,
    title: str = "DecompStat report",
    provenance: dict | None = None,
) -> None:
    """Write report as CSV, JSON, or Markdown based on file suffix."""
    p = Path(out)
    p.parent.mkdir(parents=True, exist_ok=True)
    suffix = p.suffix.lower()
    if suffix == ".csv":
        table.to_csv(p, index=False)
    elif suffix == ".json":
        payload = {
            "title": title,
            "decompstat_version": __version__,
            "provenance": provenance or {},
            "records": table.to_dict(orient="records"),
        }
        p.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
    elif suffix in {".md", ".markdown"}:
        lines = [f"# {title}", "", f"DecompStat version: `{__version__}`", ""]
        if provenance:
            lines.append("## Provenance")
            lines.append("")
            for k in sorted(provenance):
                lines.append(f"- `{k}`: `{provenance[k]}`")
            lines.append("")
        lines.append("## Results")
        lines.append("")
        lines.append(_markdown_table(table))
        lines.append("")
        p.write_text("\n".join(lines), encoding="utf-8")
    else:
        raise ValueError("Output suffix must be .csv, .json, or .md")
