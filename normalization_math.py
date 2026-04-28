"""Pure normalization and KDM formulas for SACMES."""

from sacmes_shared import KDMMethod, PlotTimeReportingMode


def calculate_low_frequency_offset(
    x_axis_mode: PlotTimeReportingMode,
    sample: float,
    file_number: int,
    low_frequency_slope: float,
    low_frequency_offset: float,
) -> float:
    offset: float
    match x_axis_mode:
        case PlotTimeReportingMode.EXPERIMENT_TIME:
            offset = sample*low_frequency_slope + low_frequency_offset
        case PlotTimeReportingMode.FILE_NUMBER:
            offset = file_number*low_frequency_slope + low_frequency_offset
    return offset


def calculate_normalized_ratio(high_point: float, low_point: float) -> float:
    return high_point/low_point


def calculate_kdm(high_point: float, low_point: float, kdm_method: KDMMethod) -> float:
    kdm: float
    match kdm_method:
        case KDMMethod.OLD:
            kdm = (high_point - low_point) + 1
        case KDMMethod.NEW:
            average: float = 0.5*(high_point + low_point)
            kdm = (high_point - low_point)/average + 1
    return kdm
