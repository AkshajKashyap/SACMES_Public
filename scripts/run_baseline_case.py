#!/usr/bin/env python3
"""Run a SACMES baseline manifest case without driving the Tk GUI."""

from __future__ import annotations

import argparse
import os
import shutil
import sys
from pathlib import Path
from typing import Any, Dict, Iterable, List


REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))
DEFAULT_MANIFEST = REPO_ROOT / "baseline" / "manifest.json"
DEFAULT_EXPORT_DIR = Path("/tmp/sacmes_baseline_exports")


class _NullWidget:
    def __init__(self, text: str = ""):
        self._text = text

    def config(self, **kwargs) -> None:
        if "text" in kwargs:
            self._text = str(kwargs["text"])

    def cget(self, key: str) -> str:
        if key == "text":
            return self._text
        return ""


def _import_sacmes():
    os.environ.setdefault("SACMES_HEADLESS", "1")
    os.environ.setdefault("MPLCONFIGDIR", "/tmp/sacmes-matplotlib")
    import SACMES  # pylint: disable=import-outside-toplevel

    return SACMES


def _case_by_id(cases: Iterable[Dict[str, Any]], case_id: str) -> Dict[str, Any]:
    for case in cases:
        if case.get("id") == case_id:
            return case
    raise ValueError(f"Case not found in manifest: {case_id}")


def _parse_frequencies(value: str) -> List[int]:
    frequencies = [int(item.strip()) for item in value.split(",") if item.strip()]
    if not frequencies:
        raise ValueError("At least one frequency is required.")
    return frequencies


def _peak_method(sacmes: Any, value: str):
    match value:
        case "poly":
            return sacmes.PeakMethod.POLY
        case "multi_gauss":
            return sacmes.PeakMethod.GAUSS
        case _:
            raise ValueError(f"Unsupported peak_method for headless runner: {value}")


def _dataset_path(case: Dict[str, Any], manifest: Dict[str, Any], override: str | None) -> Path:
    if override:
        return Path(override).expanduser().resolve()
    baseline_source = str(case.get("baseline_source", "")).strip()
    if baseline_source:
        return Path(baseline_source).expanduser().resolve()
    dataset = str(case.get("dataset", "")).strip()
    root = str(manifest.get("dataset_root", "")).strip()
    if not dataset or not root:
        raise ValueError("Case requires baseline_source or manifest dataset_root + dataset.")
    return (Path(root).expanduser() / dataset).resolve()


def _configure_runtime(
    sacmes: Any,
    *,
    case: Dict[str, Any],
    dataset_path: Path,
    export_path: Path,
    frequencies: List[int],
) -> None:
    sacmes.global_file_path = str(dataset_path) + "/"
    sacmes.global_export_path = str(export_path.parent) + "/"
    sacmes.global_file_handle = export_path.name
    sacmes.global_export_file_path = str(export_path)
    sacmes.global_data_directory = dataset_path.name
    sacmes.global_handle_variable = "E"

    sacmes.global_analysis_method = sacmes.AnalysisMethod.CONTINUOUS_SCAN
    sacmes.global_peak_method = _peak_method(sacmes, str(case.get("peak_method", "")))
    sacmes.global_kdm_method = sacmes.KDMMethod.NEW
    sacmes.global_plot_summary_mode = sacmes.PlotSummaryMode.PHE
    sacmes.global_electrodes_mode = sacmes.ElectrodesMode.SINGLE
    sacmes.global_x_axis_mode = sacmes.PlotTimeReportingMode.EXPERIMENT_TIME

    sacmes.global_current_column = 2
    sacmes.global_base_column_index_for_currents = 1
    sacmes.global_voltage_column = 1
    sacmes.global_voltage_column_index = 0
    sacmes.global_columns_per_electrode = 3
    sacmes.global_delimiter = sacmes.Delimiter.COMMA
    sacmes.global_file_encoding = sacmes.FileEncoding.UTF_8
    sacmes.global_file_name_pattern = "<H><E>_<F>Hz__<N>.txt"

    sacmes.global_electrode_list = [int(electrode) for electrode in case.get("electrodes", [])]
    if not sacmes.global_electrode_list:
        raise ValueError(f"Case has no electrodes: {case.get('id')}")
    sacmes.global_electrode_count = len(sacmes.global_electrode_list)
    sacmes.global_electrode_dict = {
        electrode: index for index, electrode in enumerate(sacmes.global_electrode_list)
    }

    sacmes.global_frequency_list = frequencies
    sacmes.global_frequency_dict = {
        frequency: index for index, frequency in enumerate(sacmes.global_frequency_list)
    }
    sacmes.global_high_frequency = max(frequencies)
    sacmes.global_low_frequency = min(frequencies)
    sacmes.global_high_low_dictionary = {
        sacmes.HighLow.HIGH: sacmes.global_high_frequency,
        sacmes.HighLow.LOW: sacmes.global_low_frequency,
    }

    sacmes.global_number_of_files_to_process = int(case["file_number"])
    sacmes.global_sample_rate = 20
    sacmes.global_resize_interval = 200
    sacmes.global_search_interval = 10
    sacmes.global_injection_point = None
    sacmes.global_injection_selected = False
    sacmes.global_initialized_normalization = False
    sacmes.global_ratiometric_check = False
    sacmes.global_normalization_point = sacmes.DEFAULT_NORMALIZATION_FILE_NUMBER
    sacmes.global_normalization_vault = [sacmes.global_normalization_point]
    sacmes.global_text_file_export_activated = True
    sacmes.global_analysis_complete = False
    sacmes.global_analysis_already_initiated = False
    sacmes.global_poison_pill = False
    sacmes.global_real_time_sample_label = _NullWidget("0")
    sacmes.global_file_label = _NullWidget("1")
    sacmes.global_norm_warning = _NullWidget("")


def _initialize_headless_storage(sacmes: Any) -> None:
    length = len(sacmes.global_frequency_list)
    file_count = sacmes.global_number_of_files_to_process
    electrode_count = sacmes.global_electrode_count

    sacmes.global_animations = []
    sacmes.global_figures = []
    sacmes.global_ratiometric_figures = []
    sacmes.global_plot_list_continuous_scan = []
    sacmes.global_ratiometric_plots = []
    sacmes.global_frame_list = [f"Electrode {electrode}" for electrode in sacmes.global_electrode_list]
    sacmes.global_file_list = []
    sacmes.global_sample_list = []

    sacmes.global_xstart = [[0.0] * length for _ in range(electrode_count)]
    sacmes.global_xend = [[0.0] * length for _ in range(electrode_count)]
    sacmes.global_xstart_entry = [[0.0] * length for _ in range(electrode_count)]
    sacmes.global_xend_entry = [[0.0] * length for _ in range(electrode_count)]
    sacmes.global_gauss_peak = [[-0.3] * length for _ in range(electrode_count)]
    sacmes.global_gauss_baseline = [[0.3] * length for _ in range(electrode_count)]
    sacmes.global_gauss_maxheight = [[20.0] * length for _ in range(electrode_count)]
    sacmes.global_gauss_solver = []

    sacmes.global_peak_list = [
        [[0.0] * file_count for _ in range(length)] for _ in range(electrode_count)
    ]
    sacmes.global_data_list = [
        [[0.0] * file_count for _ in range(length)] for _ in range(electrode_count)
    ]
    sacmes.global_normalized_data_list = [
        [[0.0] * file_count for _ in range(length)] for _ in range(electrode_count)
    ]
    sacmes.global_offset_normalized_data_list = [
        [0.0] * file_count for _ in range(electrode_count)
    ]
    sacmes.global_normalized_ratiometric_data_list = [[] for _ in range(electrode_count)]
    sacmes.global_kdm_list = [[] for _ in range(electrode_count)]

    for electrode in sacmes.global_electrode_list:
        electrode_index = sacmes.global_electrode_dict[electrode]
        for frequency in sacmes.global_frequency_list:
            frequency_index = sacmes.global_frequency_dict[frequency]
            first_file = Path(sacmes.global_file_path) / sacmes.make_file_name(1, electrode, frequency)
            if not first_file.exists():
                raise FileNotFoundError(f"Required first file is missing: {first_file}")
            potentials, _, _ = sacmes.read_data(str(first_file), electrode)
            xstart = max(potentials)
            xend = min(potentials)
            sacmes.global_xstart[electrode_index][frequency_index] = xstart
            sacmes.global_xend[electrode_index][frequency_index] = xend
            cut_value = 0
            for value in potentials:
                if abs(value) < sacmes.EPSILON:
                    cut_value += 1
            if cut_value > 0:
                potentials = potentials[:-cut_value]
            adjusted_potentials = [value for value in potentials if xend <= value <= xstart]
            sacmes.global_gauss_solver.append(
                sacmes.MultiGausFitNoise_LSE(len(adjusted_potentials), sacmes.global_options_Gauss)
            )

    sacmes.global_wait_time = sacmes.WaitTime()
    sacmes.global_track = sacmes.Track()
    sacmes.global_data_normalization = sacmes.DataNormalization()
    sacmes.global_text_file_export = sacmes.TextFileExport().initialize(
        snapshot=sacmes.text_export_snapshot()
    )


def _new_worker(sacmes: Any, electrode: int):
    worker = sacmes.ElectrochemicalAnimation.__new__(sacmes.ElectrochemicalAnimation)
    worker.electrode = electrode
    worker.num = sacmes.global_electrode_dict[electrode]
    worker.file = sacmes.STARTING_FILE_NUMBER
    worker.index = 0
    worker.count = 0
    worker.frequency_limit = len(sacmes.global_frequency_list) - 1
    worker.sample_list = []
    worker.file_list = []
    worker.frequency_axis = []
    worker.charge_axis = []
    worker.generator = worker._raw_generator
    return worker


def _run_analysis(sacmes: Any) -> None:
    workers = [_new_worker(sacmes, electrode) for electrode in sacmes.global_electrode_list]
    for file_index in range(1, sacmes.global_number_of_files_to_process + 1):
        for worker in workers:
            worker.file = file_index
            worker.index = file_index - 1
            if file_index not in worker.file_list:
                worker.file_list.append(file_index)
                worker.sample_list.append(sacmes.get_time(len(worker.file_list)))
            for frequency_index, frequency in enumerate(sacmes.global_frequency_list):
                worker.count = frequency_index
                filename = sacmes.make_file_name(file_index, worker.electrode, frequency)
                myfile = Path(sacmes.global_file_path) / filename
                if not myfile.exists():
                    raise FileNotFoundError(f"Required data file is missing: {myfile}")
                worker._raw_generator(str(myfile), frequency)
            if len(sacmes.global_frequency_list) > 1:
                worker._ratiometric_generator()
            sacmes.global_track.tracking(file_index, None)


def _capture_state(sacmes: Any, case: Dict[str, Any], manifest_path: Path, manifest: Dict[str, Any]) -> Path:
    from scripts import baseline_capture  # pylint: disable=import-outside-toplevel

    dataset_name = baseline_capture.dataset_name_from_path(sacmes.global_file_path)
    dataset_capture = baseline_capture.DEFAULT_CAPTURES_DIR / f"{dataset_name}__run_end_export.txt"
    analysis_capture = baseline_capture.DEFAULT_CAPTURES_DIR / f"{dataset_name}__analysis_finished.json"
    original_dataset_capture = dataset_capture.read_bytes() if dataset_capture.exists() else None
    original_analysis_capture = analysis_capture.read_bytes() if analysis_capture.exists() else None

    sacmes.global_analysis_complete = True
    try:
        baseline_capture.capture_analysis_finished(
            {
                "dataset_path": sacmes.global_file_path,
                "import_file_label": sacmes.global_handle_variable,
                "current_file": sacmes.global_number_of_files_to_process,
                "number_of_files_to_process": sacmes.global_number_of_files_to_process,
                "global_file_handle": sacmes.global_file_handle,
                "export_path": sacmes.global_export_file_path,
                "analysis_method": str(sacmes.global_analysis_method),
                "electrode_list": list(sacmes.global_electrode_list),
                "frequency_list": list(sacmes.global_frequency_list),
                "normalization_point": sacmes.global_normalization_point,
                "global_analysis_complete": sacmes.global_analysis_complete,
                "file_list": list(sacmes.global_file_list),
                "sample_list": list(sacmes.global_sample_list),
                "data_list": sacmes.global_data_list,
                "normalized_data_list": sacmes.global_normalized_data_list,
                "offset_normalized_data_list": sacmes.global_offset_normalized_data_list,
                "normalized_ratiometric_data_list": sacmes.global_normalized_ratiometric_data_list,
                "kdm_list": sacmes.global_kdm_list,
            },
            manifest_path=manifest_path,
        )
        actual_path = baseline_capture.resolve_path(
            str(case["actual_export"]),
            manifest=manifest,
            manifest_path=manifest_path,
            root_key="actual_export_root",
        )
        baseline_capture.ensure_parent(actual_path)
        shutil.copyfile(dataset_capture, actual_path)
        return actual_path
    finally:
        if original_dataset_capture is None:
            dataset_capture.unlink(missing_ok=True)
        else:
            dataset_capture.write_bytes(original_dataset_capture)
        if original_analysis_capture is None:
            analysis_capture.unlink(missing_ok=True)
        else:
            analysis_capture.write_bytes(original_analysis_capture)


def run_case(args: argparse.Namespace) -> Path:
    from scripts import baseline_capture  # pylint: disable=import-outside-toplevel

    manifest_path = Path(args.manifest).expanduser().resolve()
    manifest = baseline_capture.load_manifest(manifest_path)
    case = _case_by_id(baseline_capture.iter_enabled_cases(manifest), args.case_id)
    if case.get("method") != "continuous_scan":
        raise ValueError(f"Only continuous_scan cases are supported: {args.case_id}")

    dataset_path = _dataset_path(case, manifest, args.dataset_path)
    export_dir = Path(args.export_dir).expanduser().resolve()
    export_dir.mkdir(parents=True, exist_ok=True)
    export_path = export_dir / f"{args.case_id}.txt"

    sacmes = _import_sacmes()
    _configure_runtime(
        sacmes,
        case=case,
        dataset_path=dataset_path,
        export_path=export_path,
        frequencies=_parse_frequencies(args.frequencies),
    )
    _initialize_headless_storage(sacmes)
    _run_analysis(sacmes)
    return _capture_state(sacmes, case, manifest_path, manifest)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("case_id", help="Manifest case id to run.")
    parser.add_argument(
        "--manifest",
        default=str(DEFAULT_MANIFEST),
        help="Path to baseline manifest JSON. Default: baseline/manifest.json",
    )
    parser.add_argument("--dataset-path", help="Override dataset directory for this run.")
    parser.add_argument(
        "--frequencies",
        default="30,100",
        help="Comma-separated frequency list. Default: 30,100",
    )
    parser.add_argument(
        "--export-dir",
        default=str(DEFAULT_EXPORT_DIR),
        help=f"Scratch export directory. Default: {DEFAULT_EXPORT_DIR}",
    )
    return parser


def main() -> int:
    args = build_parser().parse_args()
    actual_path = run_case(args)
    print(f"Wrote case capture: {actual_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
