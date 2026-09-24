import tempfile
from pathlib import Path
from types import SimpleNamespace
from unittest import TestCase, mock

from scripts import baseline_capture, run_baseline_case


def synthetic_sacmes(dataset_path: Path) -> SimpleNamespace:
    return SimpleNamespace(
        global_file_path=str(dataset_path) + "/",
        global_handle_variable="E",
        global_number_of_files_to_process=1,
        global_file_handle="synthetic.txt",
        global_export_file_path=str(dataset_path / "synthetic.txt"),
        global_analysis_method="Continuous Scan",
        global_electrode_list=[1],
        global_frequency_list=[30, 100],
        global_normalization_point=1,
        global_analysis_complete=False,
        global_file_list=[1],
        global_sample_list=[0.0],
        global_data_list=[[[1.0], [2.0]]],
        global_normalized_data_list=[[[1.0], [1.0]]],
        global_offset_normalized_data_list=[[1.0]],
        global_normalized_ratiometric_data_list=[[1.0]],
        global_kdm_list=[[1.0]],
    )


class CaptureStateTest(TestCase):
    def setUp(self) -> None:
        self.temporary_directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary_directory.cleanup)
        self.root = Path(self.temporary_directory.name)
        self.captures = self.root / "captures"
        self.captures.mkdir()
        self.dataset = self.root / "synthetic_dataset"
        self.dataset.mkdir()
        self.sacmes = synthetic_sacmes(self.dataset)
        self.dataset_capture = self.captures / "synthetic_dataset__run_end_export.txt"
        self.analysis_capture = self.captures / "synthetic_dataset__analysis_finished.json"
        self.dataset_capture.write_text("old temporary export", encoding="utf-8")
        self.analysis_capture.write_text("old analysis capture", encoding="utf-8")

    def capture_analysis_finished(self, _state, manifest_path):
        self.assertEqual(manifest_path, self.root / "manifest.json")
        self.dataset_capture.write_text("new generated export", encoding="utf-8")
        self.analysis_capture.write_text("new analysis capture", encoding="utf-8")
        return self.analysis_capture

    def run_capture(self, actual_path: Path) -> Path:
        with (
            mock.patch.object(baseline_capture, "DEFAULT_CAPTURES_DIR", self.captures),
            mock.patch.object(
                baseline_capture,
                "capture_analysis_finished",
                side_effect=self.capture_analysis_finished,
            ),
        ):
            return run_baseline_case._capture_state(
                self.sacmes,
                {"actual_export": str(actual_path)},
                self.root / "manifest.json",
                {},
            )

    def test_same_path_preserves_new_generated_export(self):
        result = self.run_capture(self.dataset_capture)

        self.assertEqual(result, self.dataset_capture)
        self.assertEqual(self.dataset_capture.read_text(encoding="utf-8"), "new generated export")
        self.assertEqual(self.analysis_capture.read_text(encoding="utf-8"), "old analysis capture")

    def test_different_path_copies_export_and_restores_temporary_capture(self):
        actual_path = self.root / "case-specific" / "actual.txt"

        result = self.run_capture(actual_path)

        self.assertEqual(result, actual_path)
        self.assertEqual(actual_path.read_text(encoding="utf-8"), "new generated export")
        self.assertEqual(self.dataset_capture.read_text(encoding="utf-8"), "old temporary export")
        self.assertEqual(self.analysis_capture.read_text(encoding="utf-8"), "old analysis capture")
