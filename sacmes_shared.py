"""Shared fixed definitions for SACMES modules."""

from enum import Enum


class ElectrodesMode(Enum):
    SINGLE = 0
    MULTIPLE = 1


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


class PlotTimeReportingMode(Enum):
    EXPERIMENT_TIME = 0
    FILE_NUMBER = 1

    def __str__(self) -> str:
        match self:
            case PlotTimeReportingMode.EXPERIMENT_TIME:
                return "Experiment Time"
            case PlotTimeReportingMode.FILE_NUMBER:
                return "File Number"


class XBound(Enum):
    START_PLUS = 1
    NOW_MINUS = 2


class YBound(Enum):
    AUTOMATIC = 1
    MANUAL = 2


class Delimiter(Enum):
    SPACE = 1
    TAB = 2
    COMMA = 3

    def __str__(self) -> str:
        match self:
            case Delimiter.SPACE:
                return " "
            case Delimiter.TAB:
                return "\t"
            case Delimiter.COMMA:
                return ","


class FileEncoding(Enum):
    UTF_8 = 1
    UTF_16 = 2

    def __str__(self) -> str:
        match self:
            case FileEncoding.UTF_8:
                return "UTF-8"
            case FileEncoding.UTF_16:
                return "UTF-16"


class KDMMethod(Enum):
    OLD = 0
    NEW = 1

    def __str__(self) -> str:
        match self:
            case KDMMethod.OLD:
                return "Old KDM"
            case KDMMethod.NEW:
                return "New KDM"
