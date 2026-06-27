"""
Unit tests — RiskLevel domain entity
Tests the from_score factory, score_range property, and color_hex.
"""
import pytest
from backend.domain.entities.risk_level import RiskLevel


class TestRiskLevelFromScore:
    """RiskLevel.from_score() must correctly classify scores into levels."""

    def test_score_0_is_low(self):
        assert RiskLevel.from_score(0.0) == RiskLevel.LOW

    def test_score_24_9_is_low(self):
        assert RiskLevel.from_score(24.9) == RiskLevel.LOW

    def test_score_25_is_medium(self):
        assert RiskLevel.from_score(25.0) == RiskLevel.MEDIUM

    def test_score_49_9_is_medium(self):
        assert RiskLevel.from_score(49.9) == RiskLevel.MEDIUM

    def test_score_50_is_high(self):
        assert RiskLevel.from_score(50.0) == RiskLevel.HIGH

    def test_score_74_9_is_high(self):
        assert RiskLevel.from_score(74.9) == RiskLevel.HIGH

    def test_score_75_is_critical(self):
        assert RiskLevel.from_score(75.0) == RiskLevel.CRITICAL

    def test_score_100_is_critical(self):
        assert RiskLevel.from_score(100.0) == RiskLevel.CRITICAL


class TestRiskLevelScoreRange:
    """score_range property should return non-overlapping boundaries."""

    def test_all_levels_have_ranges(self):
        for level in RiskLevel:
            lo, hi = level.score_range
            assert lo < hi, f"{level} range [{lo},{hi}] invalid"

    def test_ranges_cover_full_spectrum(self):
        all_ranges = [level.score_range for level in RiskLevel]
        lo_min = min(r[0] for r in all_ranges)
        hi_max = max(r[1] for r in all_ranges)
        assert lo_min == 0.0
        assert hi_max == 100.0


class TestRiskLevelColorHex:
    """Each risk level should have a distinct, valid hex color."""

    def test_colors_are_hex(self):
        for level in RiskLevel:
            color = level.color_hex
            assert color.startswith("#"), f"{level} color {color!r} not a hex string"
            assert len(color) in {4, 7}, f"{level} color {color!r} wrong length"

    def test_colors_are_unique(self):
        colors = [level.color_hex for level in RiskLevel]
        assert len(set(colors)) == len(colors), "Duplicate colors found"


class TestRiskLevelEnum:
    """Basic enum contract tests."""

    def test_string_values(self):
        assert str(RiskLevel.LOW) == "LOW"
        assert str(RiskLevel.CRITICAL) == "CRITICAL"

    def test_is_str(self):
        # RiskLevel inherits str so it can be used in DB columns
        assert isinstance(RiskLevel.HIGH, str)

    def test_four_levels(self):
        assert len(RiskLevel) == 4


class TestPredictionEntity:
    """Tests for the Prediction domain entity validation."""

    def _make_prediction(self, risk_score: float = 55.0, confidence: float = 0.85) -> object:
        from uuid import uuid4
        from datetime import datetime, timezone
        from backend.domain.entities.prediction import Prediction

        return Prediction(
            id=uuid4(),
            area_id=uuid4(),
            predicted_for=datetime.now(timezone.utc),
            window_hours=24,
            risk_score=risk_score,
            risk_level=RiskLevel.from_score(risk_score),
            crime_type="THEFT",
            confidence=confidence,
            model_version="xgboost-v1",
        )

    def test_valid_prediction_created(self):
        pred = self._make_prediction(55.0, 0.85)
        assert pred.risk_score == 55.0
        assert pred.confidence == 0.85

    def test_invalid_risk_score_raises(self):
        with pytest.raises(ValueError, match="risk_score"):
            self._make_prediction(risk_score=150.0)

    def test_negative_risk_score_raises(self):
        with pytest.raises(ValueError, match="risk_score"):
            self._make_prediction(risk_score=-1.0)

    def test_invalid_confidence_raises(self):
        with pytest.raises(ValueError, match="confidence"):
            self._make_prediction(confidence=1.5)

    def test_boundary_risk_score_100(self):
        pred = self._make_prediction(risk_score=100.0)
        assert pred.risk_score == 100.0
