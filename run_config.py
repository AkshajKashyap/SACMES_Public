"""Immutable configuration captured when a SACMES run starts."""

from dataclasses import dataclass
from typing import Tuple

from data_io import DataIOConfig
from sacmes_shared import (
    AnalysisMethod,
    Delimiter,
    ElectrodesMode,
    FileEncoding,
    KDMMethod,
    PeakMethod,
    PlotSummaryMode,
    PlotTimeReportingMode,
)


@dataclass(frozen=True)
class RunConfig:
    """Settings that remain fixed for the lifetime of one analysis run."""

    analysis_method: AnalysisMethod
    peak_method: PeakMethod
    kdm_method: KDMMethod
    plot_summary_mode: PlotSummaryMode
    x_axis_mode: PlotTimeReportingMode
    electrodes: Tuple[int, ...]
    frequencies: Tuple[int, ...]
    electrodes_mode: ElectrodesMode
    file_name_pattern: str
    handle_variable: str
    file_encoding: FileEncoding
    delimiter: Delimiter
    voltage_column: int
    current_column: int
    columns_per_electrode: int
    number_of_files: int
    sample_rate: float
    search_interval: int
    resize_interval: int
    export_enabled: bool
    injection_enabled: bool

    def data_io_config(self) -> DataIOConfig:
        """Derive the existing parser/naming configuration for this run."""
        return DataIOConfig(
            file_name_pattern=self.file_name_pattern,
            electrodes_mode=self.electrodes_mode,
            handle_variable=self.handle_variable,
            file_encoding=self.file_encoding,
            delimiter=self.delimiter,
            voltage_column_index=self.voltage_column - 1,
            base_column_index_for_currents=self.current_column - 1,
            columns_per_electrode=self.columns_per_electrode,
        )
