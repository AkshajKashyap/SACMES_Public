from unittest import TestCase

from workflow_state import FileProgress, NormalizationRequest


class FileProgressTest(TestCase):
    def test_one_required_completion(self):
        progress = FileProgress(file_count=1, required_completions=1)

        self.assertTrue(progress.record_completion(1))

    def test_two_required_completions(self):
        progress = FileProgress(file_count=1, required_completions=2)

        self.assertFalse(progress.record_completion(1))
        self.assertTrue(progress.record_completion(1))

    def test_three_required_completions(self):
        progress = FileProgress(file_count=1, required_completions=3)

        self.assertFalse(progress.record_completion(1))
        self.assertFalse(progress.record_completion(1))
        self.assertTrue(progress.record_completion(1))

    def test_completed_file_starts_a_new_cycle(self):
        progress = FileProgress(file_count=1, required_completions=2)

        outcomes = [progress.record_completion(1) for _ in range(4)]

        self.assertEqual(outcomes, [False, True, False, True])

    def test_files_advance_independently_and_out_of_order(self):
        progress = FileProgress(file_count=2, required_completions=2)

        outcomes = [
            progress.record_completion(2),
            progress.record_completion(1),
            progress.record_completion(2),
            progress.record_completion(1),
        ]

        self.assertEqual(outcomes, [False, False, True, True])


class NormalizationRequestTest(TestCase):
    def test_request_defaults_false_and_can_be_requested_then_completed(self):
        request = NormalizationRequest()
        self.assertFalse(request.waiting)

        request.request()
        self.assertTrue(request.waiting)

        request.complete()
        self.assertFalse(request.waiting)
