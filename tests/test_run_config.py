from dataclasses import FrozenInstanceError
from unittest import TestCase

from data_io import DataIOConfig
from run_config import RunConfig
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


def make_run_config() -> RunConfig:
    return RunConfig(
        analysis_method=AnalysisMethod.CONTINUOUS_SCAN,
        peak_method=PeakMethod.POLY,
        kdm_method=KDMMethod.NEW,
        plot_summary_mode=PlotSummaryMode.PHE,
        x_axis_mode=PlotTimeReportingMode.EXPERIMENT_TIME,
        electrodes=(1, 3),
        frequencies=(30, 100),
        electrodes_mode=ElectrodesMode.SINGLE,
        file_name_pattern="<H><E>_<F>Hz__<N>.txt",
        handle_variable="E",
        file_encoding=FileEncoding.UTF_8,
        delimiter=Delimiter.COMMA,
        voltage_column=1,
        current_column=2,
        columns_per_electrode=3,
        number_of_files=10,
        sample_rate=20,
        search_interval=25,
        resize_interval=200,
        export_enabled=True,
        injection_enabled=False,
    )


class RunConfigTest(TestCase):
    def test_captures_selections_file_format_and_intervals(self):
        config = make_run_config()

        self.assertEqual(config.electrodes, (1, 3))
        self.assertEqual(config.frequencies, (30, 100))
        self.assertEqual(config.file_name_pattern, "<H><E>_<F>Hz__<N>.txt")
        self.assertEqual(config.file_encoding, FileEncoding.UTF_8)
        self.assertEqual(config.delimiter, Delimiter.COMMA)
        self.assertEqual(config.voltage_column, 1)
        self.assertEqual(config.current_column, 2)
        self.assertEqual(config.columns_per_electrode, 3)
        self.assertEqual(config.number_of_files, 10)
        self.assertEqual(config.sample_rate, 20)
        self.assertEqual(config.search_interval, 25)
        self.assertEqual(config.resize_interval, 200)

    def test_is_immutable(self):
        config = make_run_config()

        with self.assertRaises(FrozenInstanceError):
            config.number_of_files = 20

    def test_derives_existing_data_io_config(self):
        config = make_run_config()

        self.assertEqual(
            config.data_io_config(),
            DataIOConfig(
                file_name_pattern="<H><E>_<F>Hz__<N>.txt",
                electrodes_mode=ElectrodesMode.SINGLE,
                handle_variable="E",
                file_encoding=FileEncoding.UTF_8,
                delimiter=Delimiter.COMMA,
                voltage_column_index=0,
                base_column_index_for_currents=1,
                columns_per_electrode=3,
            ),
        )
