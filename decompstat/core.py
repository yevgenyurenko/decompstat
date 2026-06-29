"""Small convenience wrapper around validated DecompStat tables."""

from __future__ import annotations

from dataclasses import dataclass
import pandas as pd

from .schema import Metadata
from .io import normalize_dataframe
from .validate import validate_dataset, summarize_inventory


@dataclass
class EnergyEnsemble:
    """Validated energy-decomposition ensemble.

    This class is intentionally thin. Most public functionality is implemented as pure
    functions in compare.py, ranking.py, and uncertainty.py.
    """

    data: pd.DataFrame
    metadata: Metadata

    def __post_init__(self) -> None:
        self.data = normalize_dataframe(self.data)
        validate_dataset(self.data, self.metadata, require_snapshot_assertion=False)

    def summarize(self) -> pd.DataFrame:
        """Return inventory summary grouped by system/state/method/component."""
        return summarize_inventory(self.data)
