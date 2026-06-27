"""
CrimePatrol Domain — Risk Level Enum
Pure Python enum with no framework dependencies.
"""
from enum import Enum


class RiskLevel(str, Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"

    @property
    def score_range(self) -> tuple[float, float]:
        """Returns (min_score, max_score) for this risk level."""
        return {
            RiskLevel.LOW: (0.0, 25.0),
            RiskLevel.MEDIUM: (25.0, 50.0),
            RiskLevel.HIGH: (50.0, 75.0),
            RiskLevel.CRITICAL: (75.0, 100.0),
        }[self]

    @classmethod
    def from_score(cls, score: float) -> "RiskLevel":
        """Derive risk level from a 0–100 risk score."""
        if score < 25.0:
            return cls.LOW
        if score < 50.0:
            return cls.MEDIUM
        if score < 75.0:
            return cls.HIGH
        return cls.CRITICAL

    @property
    def color_hex(self) -> str:
        """UI color for this risk level."""
        return {
            RiskLevel.LOW: "#22c55e",
            RiskLevel.MEDIUM: "#f59e0b",
            RiskLevel.HIGH: "#ef4444",
            RiskLevel.CRITICAL: "#7c3aed",
        }[self]
