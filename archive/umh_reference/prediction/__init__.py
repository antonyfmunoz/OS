"""Prediction — intent modeling, behavioral prediction, speculative planning, accuracy tracking, adaptive weighting, cross-session memory, and pattern matching."""

from umh.prediction.calibrator import (
    CalibrationResult,
    ConfidenceCalibrator,
    ThresholdAdapter,
)
from umh.prediction.evaluator import MatchResult, PredictionEvaluator
from umh.prediction.intent import UserIntent, make_intent_id
from umh.prediction.matcher import MatchDetail, PredictionMatcher
from umh.prediction.metrics import (
    ConfidenceBucket,
    PredictionAccuracy,
    PredictionMetrics,
    SourceAccuracy,
)
from umh.prediction.persistence import (
    FilePredictionBackend,
    PersistenceStats,
)
from umh.prediction.planner import PredictedPlan, PredictionPolicy, PredictivePlanner
from umh.prediction.predictor import PredictionContext, Predictor
from umh.prediction.store import (
    PredictionRecord,
    PredictionStatus,
    PredictionStore,
    record_from_intent,
)
from umh.prediction.temporal import DecayResult, TemporalWeighter
from umh.prediction.weights import PredictionWeight, WeightStore

__all__ = [
    "CalibrationResult",
    "ConfidenceBucket",
    "ConfidenceCalibrator",
    "DecayResult",
    "FilePredictionBackend",
    "MatchDetail",
    "MatchResult",
    "PersistenceStats",
    "PredictedPlan",
    "PredictionAccuracy",
    "PredictionContext",
    "PredictionEvaluator",
    "PredictionMatcher",
    "PredictionMetrics",
    "PredictionPolicy",
    "PredictionRecord",
    "PredictionStatus",
    "PredictionStore",
    "PredictionWeight",
    "PredictivePlanner",
    "Predictor",
    "SourceAccuracy",
    "TemporalWeighter",
    "ThresholdAdapter",
    "UserIntent",
    "WeightStore",
    "make_intent_id",
    "record_from_intent",
]
