import os
from unittest import TestCase, mock

os.environ["SACMES_HEADLESS"] = "1"

import SACMES as sacmes
from sacmes_shared import AnalysisMethod


class TrackCharacterizationTest(TestCase):
    def setUp(self):
        sacmes.global_number_of_files_to_process = 3
        sacmes.global_analysis_method = AnalysisMethod.CONTINUOUS_SCAN
        sacmes.global_text_file_export_activated = False
        sacmes.global_ratiometric_check = False
        sacmes.global_data_normalization = mock.Mock()
        self.update_global_lists = mock.patch.object(sacmes, "_update_global_lists").start()
        self.addCleanup(mock.patch.stopall)

    def make_track(self, electrode_count):
        sacmes.global_electrode_count = electrode_count
        return sacmes.Track()

    def test_one_electrode_completes_on_first_notification(self):
        track = self.make_track(electrode_count=1)

        track.tracking(file=1, frequency=None)

        self.update_global_lists.assert_called_once_with(1)

    def test_two_electrodes_complete_on_second_notification(self):
        track = self.make_track(electrode_count=2)

        track.tracking(file=1, frequency=None)
        self.update_global_lists.assert_not_called()
        track.tracking(file=1, frequency=None)

        self.update_global_lists.assert_called_once_with(1)

    def test_three_electrodes_complete_on_third_notification(self):
        track = self.make_track(electrode_count=3)

        track.tracking(file=1, frequency=None)
        track.tracking(file=1, frequency=None)
        self.update_global_lists.assert_not_called()
        track.tracking(file=1, frequency=None)

        self.update_global_lists.assert_called_once_with(1)

    def test_completed_file_starts_a_fresh_full_cycle(self):
        track = self.make_track(electrode_count=2)

        for _ in range(4):
            track.tracking(file=1, frequency=None)

        self.assertEqual(self.update_global_lists.call_args_list, [mock.call(1), mock.call(1)])

    def test_out_of_order_files_keep_independent_progress(self):
        track = self.make_track(electrode_count=2)

        track.tracking(file=2, frequency=None)
        track.tracking(file=1, frequency=None)
        track.tracking(file=2, frequency=None)
        track.tracking(file=1, frequency=None)

        self.assertEqual(self.update_global_lists.call_args_list, [mock.call(2), mock.call(1)])

    def test_continuous_completion_runs_side_effects_once_in_order(self):
        events = []
        sacmes.global_electrode_count = 2
        sacmes.global_text_file_export_activated = True
        sacmes.global_ratiometric_check = True
        sacmes.global_data_normalization = mock.Mock()
        sacmes.global_text_file_export = mock.Mock()
        self.update_global_lists.side_effect = lambda file: events.append(("update", file))
        sacmes.global_data_normalization.renormalize_data.side_effect = \
            lambda file: events.append(("renormalize", file))
        sacmes.global_text_file_export.continuous_scan_export.side_effect = \
            lambda file, snapshot: events.append(("export", file, snapshot))
        sacmes.global_data_normalization.reset_ratiometric_data.side_effect = \
            lambda: events.append(("reset_ratiometric",))
        sacmes.global_text_file_export.txt_file_normalization.side_effect = \
            lambda: events.append(("rewrite_export",))
        snapshot = object()

        with mock.patch.object(sacmes, "text_export_snapshot", return_value=snapshot):
            track = sacmes.Track()
            track.tracking(file=1, frequency=None)
            self.assertEqual(events, [])
            track.tracking(file=1, frequency=None)

        self.assertEqual(
            events,
            [
                ("update", 1),
                ("renormalize", 1),
                ("export", 1, snapshot),
                ("reset_ratiometric",),
                ("rewrite_export",),
            ],
        )
        self.assertFalse(sacmes.global_ratiometric_check)


class NormalizationRequestIntegrationTest(TestCase):
    def test_waiting_state_defaults_requests_and_clears(self):
        sacmes.global_normalization_request = sacmes.NormalizationRequest()
        self.assertFalse(sacmes.global_normalization_request.waiting)

        sacmes.global_normalization_request.request()
        self.assertTrue(sacmes.global_normalization_request.waiting)

        sacmes.global_normalization_request.complete()
        self.assertFalse(sacmes.global_normalization_request.waiting)
