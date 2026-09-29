from unittest import TestCase

from normalization_math import (
    calculate_kdm,
    calculate_low_frequency_offset,
    calculate_normalized_ratio,
)
from sacmes_shared import KDMMethod, PlotTimeReportingMode


class LowFrequencyOffsetTest(TestCase):
    def test_experiment_time_uses_sample(self):
        result = calculate_low_frequency_offset(
            PlotTimeReportingMode.EXPERIMENT_TIME,
            sample=2.5,
            file_number=7,
            low_frequency_slope=1.2,
            low_frequency_offset=-0.5,
        )

        self.assertAlmostEqual(result, 2.5)

    def test_file_number_mode_uses_file_number(self):
        result = calculate_low_frequency_offset(
            PlotTimeReportingMode.FILE_NUMBER,
            sample=2.5,
            file_number=7,
            low_frequency_slope=1.2,
            low_frequency_offset=-0.5,
        )

        self.assertAlmostEqual(result, 7.9)


class NormalizedRatioTest(TestCase):
    def test_non_unit_ratio(self):
        self.assertAlmostEqual(calculate_normalized_ratio(3.0, 2.0), 1.5)

    def test_ratio_below_one(self):
        self.assertAlmostEqual(calculate_normalized_ratio(2.0, 5.0), 0.4)


class KDMTest(TestCase):
    def test_old_and_new_methods_have_expected_distinct_values(self):
        old_result = calculate_kdm(3.0, 1.0, KDMMethod.OLD)
        new_result = calculate_kdm(3.0, 1.0, KDMMethod.NEW)

        self.assertAlmostEqual(old_result, 3.0)
        self.assertAlmostEqual(new_result, 2.0)

    def test_equal_high_and_low_points_return_one_for_both_methods(self):
        for method in KDMMethod:
            with self.subTest(method=method):
                self.assertAlmostEqual(calculate_kdm(2.5, 2.5, method), 1.0)
