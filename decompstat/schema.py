"""Schema definitions and metadata handling for DecompStat."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any
import json

try:
    import yaml
except Exception:  # pragma: no cover - dependency should normally exist
    yaml = None


class SchemaError(ValueError):
    """Raised when input data or metadata violate the DecompStat schema."""


REQUIRED_COLUMNS = [
    "sample_id",
    "system_id",
    "state_id",
    "method_id",
    "res_1",
    "res_2",
    "energy_total",
]

OPTIONAL_COLUMNS = [
    "frame_id",
    "replica_id",
    "time_ps",
    "energy_unit",
    "component",
]

DEFAULT_COMPONENT = "total"
VALID_SIGN_CONVENTIONS = {"negative_is_stabilizing", "positive_is_stabilizing"}
VALID_UNITS = {"kcal/mol", "kJ/mol"}


@dataclass(frozen=True)
class Metadata:
    """Dataset-level metadata that must not silently drift row by row."""

    schema_version: str = "0.1"
    energy_unit: str = "kcal/mol"
    sign_convention: str = "negative_is_stabilizing"
    snapshots_shared_across_methods: bool = False
    snapshot_definition: str = ""
    provenance: dict[str, Any] = field(default_factory=dict)

    def validate(self) -> None:
        if self.energy_unit not in VALID_UNITS:
            raise SchemaError(
                f"Unsupported energy_unit={self.energy_unit!r}. Supported: {sorted(VALID_UNITS)}"
            )
        if self.sign_convention not in VALID_SIGN_CONVENTIONS:
            raise SchemaError(
                "Unsupported sign_convention="
                f"{self.sign_convention!r}. Supported: {sorted(VALID_SIGN_CONVENTIONS)}"
            )
        if not isinstance(self.snapshots_shared_across_methods, bool):
            raise SchemaError("snapshots_shared_across_methods must be true or false.")


def load_metadata(path: str | Path | None) -> Metadata:
    """Load metadata from JSON/YAML, or return conservative defaults if path is None."""
    if path is None:
        meta = Metadata()
        meta.validate()
        return meta

    p = Path(path)
    if not p.exists():
        raise FileNotFoundError(p)

    text = p.read_text(encoding="utf-8")
    if p.suffix.lower() in {".yaml", ".yml"}:
        if yaml is None:
            raise RuntimeError("PyYAML is required to read YAML metadata files.")
        raw = yaml.safe_load(text) or {}
    elif p.suffix.lower() == ".json":
        raw = json.loads(text)
    else:
        raise SchemaError("Metadata sidecar must be .json, .yaml, or .yml")

    allowed = {field.name for field in Metadata.__dataclass_fields__.values()}
    unknown = sorted(set(raw) - allowed)
    if unknown:
        raise SchemaError(f"Unknown metadata fields: {unknown}")

    meta = Metadata(**raw)
    meta.validate()
    return meta


def dump_metadata_template(path: str | Path) -> None:
    """Write a conservative metadata template."""
    p = Path(path)
    template = {
        "schema_version": "0.1",
        "energy_unit": "kcal/mol",
        "sign_convention": "negative_is_stabilizing",
        "snapshots_shared_across_methods": True,
        "snapshot_definition": "sample_id denotes the same physical snapshot across compared methods",
        "provenance": {
            "MM_MM": "custom workflow",
            "SQM_MM": "custom workflow",
        },
    }
    if p.suffix.lower() in {".yaml", ".yml"}:
        if yaml is None:
            raise RuntimeError("PyYAML is required to write YAML metadata files.")
        p.write_text(yaml.safe_dump(template, sort_keys=False), encoding="utf-8")
    elif p.suffix.lower() == ".json":
        p.write_text(json.dumps(template, indent=2), encoding="utf-8")
    else:
        raise SchemaError("Metadata sidecar must be .json, .yaml, or .yml")
