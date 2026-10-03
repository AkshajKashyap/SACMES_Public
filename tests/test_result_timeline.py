from unittest import TestCase, mock

from result_timeline import ContinuousScanTimeline


class ContinuousScanTimelineTest(TestCase):
    def test_new_instance_has_independent_empty_lists(self):
        timeline = ContinuousScanTimeline()

        self.assertEqual(timeline.files, [])
        self.assertEqual(timeline.samples, [])
        self.assertIsNot(timeline.files, timeline.samples)

    def test_record_adds_one_paired_file_and_sample(self):
        timeline = ContinuousScanTimeline()

        accepted = timeline.record(2, lambda completed_count: completed_count * 0.25)

        self.assertTrue(accepted)
        self.assertEqual(timeline.files, [2])
        self.assertEqual(timeline.samples, [0.25])

    def test_multiple_records_preserve_order_and_pairing(self):
        timeline = ContinuousScanTimeline()

        timeline.record(3, lambda _completed_count: 0.75)
        timeline.record(1, lambda _completed_count: 1.25)

        self.assertEqual(timeline.files, [3, 1])
        self.assertEqual(timeline.samples, [0.75, 1.25])
        self.assertEqual(len(timeline.files), len(timeline.samples))

    def test_duplicate_is_rejected_without_requesting_another_sample(self):
        timeline = ContinuousScanTimeline()
        timeline.record(1, lambda _completed_count: 0.5)
        sample_for_completed_count = mock.Mock(return_value=9.0)

        accepted = timeline.record(1, sample_for_completed_count)

        self.assertFalse(accepted)
        self.assertEqual(timeline.files, [1])
        self.assertEqual(timeline.samples, [0.5])
        sample_for_completed_count.assert_not_called()

    def test_two_instances_do_not_share_lists(self):
        first = ContinuousScanTimeline()
        second = ContinuousScanTimeline()

        first.record(1, lambda _completed_count: 0.5)

        self.assertEqual(second.files, [])
        self.assertEqual(second.samples, [])
        self.assertIsNot(first.files, second.files)
        self.assertIsNot(first.samples, second.samples)
