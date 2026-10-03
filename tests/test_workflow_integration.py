import os
from unittest import TestCase, mock

os.environ["SACMES_HEADLESS"] = "1"

import SACMES as sacmes
from sacmes_shared import AnalysisMethod


class UpdateGlobalListsCharacterizationTest(TestCase):
    def setUp(self):
        sacmes._initialize_continuous_scan_timeline()
        sacmes.global_number_of_files_to_process = 3
        sacmes.global_real_time_sample_label = mock.Mock()
        sacmes.global_file_label = mock.Mock()

    def test_first_unique_file_appends_rounded_paired_sample(self):
        def get_time(completed_file_count):
            self.assertEqual(sacmes.global_file_list, [2])
            self.assertEqual(completed_file_count, 1)
            return 1.23456

        with mock.patch.object(sacmes, "get_time", side_effect=get_time) as get_time_mock:
            sacmes._update_global_lists(2)

        self.assertEqual(sacmes.global_file_list, [2])
        self.assertEqual(sacmes.global_sample_list, [1.235])
        self.assertEqual(len(sacmes.global_file_list), len(sacmes.global_sample_list))
        get_time_mock.assert_called_once_with(1)
        sacmes.global_real_time_sample_label.config.assert_called_once_with(text="1.235")
        sacmes.global_file_label.config.assert_called_once_with(text="3")

    def test_duplicate_file_changes_neither_list_or_labels(self):
        sacmes.global_continuous_scan_timeline.record(
            1,
            lambda _completed_count: 0.125,
        )

        with mock.patch.object(sacmes, "get_time") as get_time_mock:
            sacmes._update_global_lists(1)

        self.assertEqual(sacmes.global_file_list, [1])
        self.assertEqual(sacmes.global_sample_list, [0.125])
        self.assertEqual(len(sacmes.global_file_list), len(sacmes.global_sample_list))
        get_time_mock.assert_not_called()
        sacmes.global_real_time_sample_label.config.assert_not_called()
        sacmes.global_file_label.config.assert_not_called()

    def test_out_of_order_files_preserve_notification_order_and_pairing(self):
        with mock.patch.object(sacmes, "get_time", side_effect=[0.1114, 0.2226, 0.3333]) as get_time_mock:
            for file in (2, 1, 3):
                sacmes._update_global_lists(file)
                self.assertEqual(len(sacmes.global_file_list), len(sacmes.global_sample_list))

        self.assertEqual(sacmes.global_file_list, [2, 1, 3])
        self.assertEqual(sacmes.global_sample_list, [0.111, 0.223, 0.333])
        self.assertEqual(
            get_time_mock.call_args_list,
            [mock.call(1), mock.call(2), mock.call(3)],
        )

    def test_file_label_advances_for_nonfinal_files_only(self):
        with mock.patch.object(sacmes, "get_time", side_effect=[0.1, 0.2]):
            sacmes._update_global_lists(1)
            sacmes._update_global_lists(3)

        self.assertEqual(
            sacmes.global_file_label.config.call_args_list,
            [mock.call(text="2")],
        )

    def test_legacy_lists_are_exact_timeline_aliases(self):
        self.assertIs(
            sacmes.global_file_list,
            sacmes.global_continuous_scan_timeline.files,
        )
        self.assertIs(
            sacmes.global_sample_list,
            sacmes.global_continuous_scan_timeline.samples,
        )

    def test_new_run_gets_fresh_owner_and_list_identities(self):
        first_timeline = sacmes.global_continuous_scan_timeline
        first_files = sacmes.global_file_list
        first_samples = sacmes.global_sample_list
        first_timeline.record(1, lambda _completed_count: 0.0)

        sacmes._initialize_continuous_scan_timeline()

        self.assertIsNot(sacmes.global_continuous_scan_timeline, first_timeline)
        self.assertIsNot(sacmes.global_file_list, first_files)
        self.assertIsNot(sacmes.global_sample_list, first_samples)
        self.assertEqual(sacmes.global_file_list, [])
        self.assertEqual(sacmes.global_sample_list, [])
        self.assertIs(
            sacmes.global_file_list,
            sacmes.global_continuous_scan_timeline.files,
        )
        self.assertIs(
            sacmes.global_sample_list,
            sacmes.global_continuous_scan_timeline.samples,
        )


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
