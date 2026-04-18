"""Frozen context object passed to every detector."""

from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

import pandas as pd

from app.matcher.config import MatcherConfig


@dataclass(frozen=True, slots=True)
class MatcherContext:
    """Read-only snapshot of the data for one dataset.

    Detectors must not mutate these frames. If a working copy is needed, call
    ``.copy()`` at the boundary.
    """

    dataset_id: UUID
    zem: pd.DataFrame
    ner: pd.DataFrame
    persons: pd.DataFrame
    config: MatcherConfig
