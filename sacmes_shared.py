"""Shared fixed definitions for SACMES modules."""

from enum import Enum


class PlotSummaryMode(Enum):
    PHE = 0
    AUC = 1

    def __str__(self) -> str:
        match self:
            case PlotSummaryMode.PHE:
                return "Peak Height Extraction"
            case PlotSummaryMode.AUC:
                return "Area Under the Curve"


class AnalysisMethod(Enum):
    CONTINUOUS_SCAN = 0
    FREQUENCY_MAP = 1

    def __str__(self) -> str:
        match self:
            case AnalysisMethod.CONTINUOUS_SCAN:
                return "Continuous Scan"
            case AnalysisMethod.FREQUENCY_MAP:
                return "Frequency Map"


class PeakMethod(Enum):
    POLY = 0
    GAUSS = 1

    def __str__(self) -> str:
        match self:
            case PeakMethod.POLY:
                return "Poly Fit"
            case PeakMethod.GAUSS:
                return "Multi-Gauss"


class HighLow(Enum):
    HIGH = 0
    LOW = 1
