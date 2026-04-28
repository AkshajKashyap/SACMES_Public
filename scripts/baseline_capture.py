#!/usr/bin/env python3
"""Local-only helpers for seeding and writing baseline capture artifacts."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, Optional


REPO_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_MANIFEST = REPO_ROOT / "baseline" / "manifest.json"
DEFAULT_EXPECTED_DIR = REPO_ROOT / "baseline" / "expected"
DEFAULT_CAPTURES_DIR = REPO_ROOT / "baseline" / "captures"


def load_manifest(manifest_path: Path = DEFAULT_MANIFEST) -> Dict[str, Any]:
    with manifest_path.open("r", encoding="utf-8") as handle:
        manifest = json.load(handle)
    if not isinstance(manifest, dict):
        raise ValueError("Manifest root must be a JSON object.")
    manifest.setdefault("dataset_root", "")
    manifest.setdefault("baseline_seed_root", manifest.get("dataset_root", ""))
    manifest.setdefault("actual_export_root", "")
    manifest.setdefault("snapshot_allowlist", [])
    manifest.setdefault("cases", [])
    return manifest


def repo_relative(path: Path) -> str:
    try:
        return str(path.relative_to(REPO_ROOT))
    except ValueError:
        return str(path)


def resolve_path(
    path_value: str,
    *,
    manifest: Dict[str, Any],
    manifest_path: Path,
    root_key: str,
) -> Path:
    path = Path(path_value).expanduser()
    if path.is_absolute():
        return path
    if path.parts and path.parts[0] == "baseline":
        return REPO_ROOT / path
    root_value = str(manifest.get(root_key, "")).strip()
    if root_value:
        return Path(root_value).expanduser() / path
    return manifest_path.parent / path


def dataset_name_from_path(path_value: str) -> str:
    normalized = path_value.rstrip("/\\")
    if not normalized:
        return ""
    return os.path.basename(normalized)


def allowlisted_dataset(manifest: Dict[str, Any], dataset_name: str) -> bool:
    allowlist = manifest.get("snapshot_allowlist", [])
    if not isinstance(allowlist, list):
        return False
    return dataset_name in allowlist


def ensure_parent(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)


def file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(65536), b""):
            digest.update(chunk)
    return digest.hexdigest()


def file_line_count(path: Path) -> int:
    with path.open("r", encoding="utf-8", errors="replace") as handle:
        return sum(1 for _ in handle)


def series_summary(values: Any) -> Dict[str, Any]:
    if not isinstance(values, list) or not values:
        return {"length": 0, "min": None, "max": None}
    try:
        return {
            "length": len(values),
            "min": min(values),
            "max": max(values),
        }
    except TypeError:
        return {"length": len(values), "min": None, "max": None}


def _json_safe(value: Any) -> Any:
    if isinstance(value, (str, int, float, bool)) or value is None:
        return value
    if isinstance(value, dict):
        return {str(key): _json_safe(val) for key, val in value.items()}
    if isinstance(value, (list, tuple)):
        return [_json_safe(item) for item in value]
    return repr(value)


def _write_json_capture(filename: str, payload: Dict[str, Any]) -> Path:
    DEFAULT_CAPTURES_DIR.mkdir(parents=True, exist_ok=True)
    capture_path = DEFAULT_CAPTURES_DIR / filename
    ensure_parent(capture_path)
    with capture_path.open("w", encoding="utf-8") as handle:
        json.dump(payload, handle, indent=2, sort_keys=True)
        handle.write("\n")
    return capture_path


def capture_analysis_finished(state: Dict[str, Any], manifest_path: Path = DEFAULT_MANIFEST) -> Optional[Path]:
    manifest = load_manifest(manifest_path)
    dataset_name = dataset_name_from_path(str(state.get("dataset_path", "")))
    if not dataset_name or not allowlisted_dataset(manifest, dataset_name):
        return None
    export_path_value = str(state.get("export_path", ""))
    export_path = Path(export_path_value)
    payload = {
        "captured_at_utc": datetime.now(timezone.utc).isoformat(),
        "event": "analysis_finished",
        "dataset_name": dataset_name,
        "debug_summary": {
            "dataset_path": state.get("dataset_path"),
            "import_file_label": state.get("import_file_label"),
            "current_file": state.get("current_file"),
            "number_of_files_to_process": state.get("number_of_files_to_process"),
            "electrode_list": _json_safe(state.get("electrode_list")),
            "frequency_list": _json_safe(state.get("frequency_list")),
            "global_file_handle": state.get("global_file_handle"),
            "export_path": state.get("export_path"),
            "file_list": series_summary(state.get("file_list")),
            "sample_list": series_summary(state.get("sample_list")),
        },
        "state": _json_safe(state),
    }
    if export_path_value and export_path.exists():
        preserved_export_path = DEFAULT_CAPTURES_DIR / f"{dataset_name}__run_end_export.txt"
        ensure_parent(preserved_export_path)
        shutil.copyfile(export_path, preserved_export_path)
        payload["run_end_export"] = {
            "source_path": export_path_value,
            "preserved_path": str(preserved_export_path),
            "sha256": file_sha256(preserved_export_path),
            "size_bytes": preserved_export_path.stat().st_size,
            "line_count": file_line_count(preserved_export_path),
        }
    filename = f"{dataset_name}__analysis_finished.json"
    return _write_json_capture(filename, payload)


def capture_export_rewrite(state: Dict[str, Any], manifest_path: Path = DEFAULT_MANIFEST) -> Optional[Path]:
    manifest = load_manifest(manifest_path)
    dataset_name = dataset_name_from_path(str(state.get("dataset_path", "")))
    if not dataset_name or not allowlisted_dataset(manifest, dataset_name):
        return None
    export_path_value = str(state.get("export_path", ""))
    export_path = Path(export_path_value)
    payload = {
        "captured_at_utc": datetime.now(timezone.utc).isoformat(),
        "event": "export_rewrite_complete",
        "dataset_name": dataset_name,
        "state": _json_safe(state),
    }
    if export_path_value and export_path.exists():
        payload["export_file"] = {
            "path": export_path_value,
            "sha256": file_sha256(export_path),
            "size_bytes": export_path.stat().st_size,
        }
    filename = f"{dataset_name}__export_rewrite.json"
    return _write_json_capture(filename, payload)


def iter_enabled_cases(manifest: Dict[str, Any]) -> Iterable[Dict[str, Any]]:
    for case in manifest.get("cases", []):
        if not isinstance(case, dict):
            continue
        if case.get("enabled", True):
            yield case


def seed_expected(manifest_path: Path = DEFAULT_MANIFEST, *, force: bool = False) -> int:
    manifest = load_manifest(manifest_path)
    copied = 0
    for case in iter_enabled_cases(manifest):
        case_id = str(case.get("id", "<missing-id>"))
        source_value = str(case.get("expected_source", "")).strip()
        baseline_value = str(case.get("expected_baseline", "")).strip()
        if not source_value or not baseline_value:
            print(f"SKIP {case_id}: missing expected_source or expected_baseline")
            continue
        source_path = resolve_path(
            source_value,
            manifest=manifest,
            manifest_path=manifest_path,
            root_key="baseline_seed_root",
        )
        baseline_path = resolve_path(
            baseline_value,
            manifest=manifest,
            manifest_path=manifest_path,
            root_key="baseline_seed_root",
        )
        if not source_path.exists():
            print(f"SKIP {case_id}: source missing: {source_path}")
            continue
        if baseline_path.exists() and not force:
            print(f"SKIP {case_id}: baseline already exists: {baseline_path}")
            continue
        ensure_parent(baseline_path)
        shutil.copyfile(source_path, baseline_path)
        copied += 1
        print(f"COPIED {case_id}: {source_path} -> {baseline_path}")
    return copied


def list_cases(manifest_path: Path = DEFAULT_MANIFEST) -> int:
    manifest = load_manifest(manifest_path)
    count = 0
    for case in iter_enabled_cases(manifest):
        count += 1
        print(f"{case.get('id', '<missing-id>')}: {case.get('dataset', '<missing-dataset>')}")
    print(f"Enabled cases: {count}")
    return count


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Manage local-only baseline capture artifacts.")
    parser.add_argument(
        "--manifest",
        default=str(DEFAULT_MANIFEST),
        help="Path to baseline manifest JSON. Default: baseline/manifest.json",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    seed_parser = subparsers.add_parser("seed-expected", help="Copy expected_source files into baseline/expected.")
    seed_parser.add_argument("--force", action="store_true", help="Overwrite existing baseline files.")

    subparsers.add_parser("list-cases", help="List enabled manifest cases.")
    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    manifest_path = Path(args.manifest).expanduser().resolve()
    if args.command == "seed-expected":
        copied = seed_expected(manifest_path, force=bool(args.force))
        print(f"Copied baseline files: {copied}")
        return 0
    if args.command == "list-cases":
        list_cases(manifest_path)
        return 0
    parser.error(f"Unsupported command: {args.command}")
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
