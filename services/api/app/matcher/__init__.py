"""Pandas-powered matcher engine. Detectors live in ``app.matcher.detectors``."""

from app.matcher.config import MatcherConfig, default_config
from app.matcher.context import MatcherContext
from app.matcher.engine import MatcherResult, run as run_matcher

__all__ = ["MatcherConfig", "MatcherContext", "MatcherResult", "default_config", "run_matcher"]
