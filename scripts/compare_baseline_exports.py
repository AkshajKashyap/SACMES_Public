#!/usr/bin/env python3
"""Compare actual exports against local baseline files."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any, Dict, Iterable, Tuple


REPO_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_MANIFEST = REPO_ROOT / "baseline" / "manifest.json"


def load_manifest(manifest_path: Path) -> Dict[str, Any]:
    with manifest_path.open("r", encoding="utf-8") as handle:
        manifest = json.load(handle)
    if not isinstance(manifest, dict):
        raise ValueError("Manifest root must be a JSON object.")
    manifest.setdefault("actual_export_root", "")
    manifest.setdefault("cases", [])
    return manifest


def iter_enabled_cases(manifest: Dict[str, Any]) -> Iterable[Dict[str, Any]]:
    for case in manifest.get("cases", []):
        if isinstance(case, dict) and case.get("enabled", True):
            yield case


def resolve_expected_path(path_value: str, *, manifest_path: Path) -> Path:
    path = Path(path_value).expanduser()
    if path.is_absolute():
        return path
    if path.parts and path.parts[0] == "baseline":
        return REPO_ROOT / path
    return manifest_path.parent / path


def resolve_actual_path(path_value: str, *, manifest: Dict[str, Any], manifest_path: Path) -> Tuple[Path | None, str | None]:
    path = Path(path_value).expanduser()
    if path.is_absolute():
        return path, None
    if path.parts and path.parts[0] == "baseline":
        return REPO_ROOT / path, None
    actual_export_root = str(manifest.get("actual_export_root", "")).strip()
    if actual_export_root:
        return Path(actual_export_root).expanduser() / path, None
    return None, "Relative actual_export requires an explicit actual_export_root; legacy dataset_root fallback is disabled."


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def diff_location(expected: bytes, actual: bytes) -> Tuple[int, int, int]:
    limit = min(len(expected), len(actual))
    offset = 0
    while offset < limit and expected[offset] == actual[offset]:
        offset += 1
    line = expected[:offset].count(b"\n") + 1
    line_start = expected.rfind(b"\n", 0, offset)
    if line_start == -1:
        column = offset + 1
    else:
        column = offset - line_start
    return offset, line, column


def render_byte(value: int | None) -> str:
    if value is None:
        return "<EOF>"
    if 32 <= value <= 126:
        return f"{value} ('{chr(value)}')"
    return str(value)


def compare_numeric_text(expected_text: str, actual_text: str, tolerance: float) -> Tuple[bool, str | None]:
    expected_lines = expected_text.splitlines()
    actual_lines = actual_text.splitlines()
    if len(expected_lines) != len(actual_lines):
        return False, f"line count differs: expected={len(expected_lines)} actual={len(actual_lines)}"
    for line_number, (expected_line, actual_line) in enumerate(zip(expected_lines, actual_lines), start=1):
        if expected_line == actual_line:
            continue
        expected_fields = expected_line.split()
        actual_fields = actual_line.split()
        if len(expected_fields) != len(actual_fields):
            return False, (
                f"field count differs at line {line_number}: "
                f"expected={len(expected_fields)} actual={len(actual_fields)}"
            )
        for column, (expected_field, actual_field) in enumerate(
            zip(expected_fields, actual_fields),
            start=1,
        ):
            if expected_field == actual_field:
                continue
            try:
                expected_float = float(expected_field)
                actual_float = float(actual_field)
            except ValueError:
                return False, (
                    f"text differs at line {line_number} column {column}: "
                    f"expected={expected_field!r} actual={actual_field!r}"
                )
            difference = abs(expected_float - actual_float)
            if difference > tolerance:
                return False, (
                    f"numeric difference exceeds tolerance at line {line_number} "
                    f"column {column}: expected={expected_field} actual={actual_field} "
                    f"abs_diff={difference} tolerance={tolerance}"
                )
    return True, None


def compare_case(case: Dict[str, Any], *, manifest: Dict[str, Any], manifest_path: Path) -> str:
    case_id = str(case.get("id", "<missing-id>"))
    expected_value = str(case.get("expected_baseline", "")).strip()
    actual_value = str(case.get("actual_export", "")).strip()
    if not expected_value or not actual_value:
        print(f"SKIP {case_id}")
        print("  Missing expected_baseline or actual_export in manifest.")
        return "skip"

    expected_path = resolve_expected_path(expected_value, manifest_path=manifest_path)
    actual_path, actual_path_error = resolve_actual_path(actual_value, manifest=manifest, manifest_path=manifest_path)
    if actual_path_error is not None:
        print(f"SKIP {case_id}")
        print(f"  {actual_path_error}")
        print(f"  actual_export={actual_value}")
        return "skip"
    if not expected_path.exists():
        print(f"FAIL {case_id}")
        print(f"  Expected baseline missing: {expected_path}")
        return "fail"
    if actual_path is None or not actual_path.exists():
        print(f"SKIP {case_id}")
        print(f"  Actual export missing: {actual_path}")
        return "skip"

    expected_bytes = expected_path.read_bytes()
    actual_bytes = actual_path.read_bytes()
    if expected_bytes == actual_bytes:
        print(f"PASS {case_id}")
        print(f"  sha256={sha256_bytes(actual_bytes)}")
        return "pass"

    numeric_tolerance = case.get("numeric_tolerance")
    if numeric_tolerance is not None:
        tolerance = float(numeric_tolerance)
        numeric_match, numeric_error = compare_numeric_text(
            expected_bytes.decode("utf-8", errors="replace"),
            actual_bytes.decode("utf-8", errors="replace"),
            tolerance,
        )
        if numeric_match:
            print(f"PASS {case_id}")
            print(f"  numeric_tolerance={tolerance}")
            print(f"  expected_sha256={sha256_bytes(expected_bytes)}")
            print(f"  actual_sha256={sha256_bytes(actual_bytes)}")
            return "pass"
        print(f"  Numeric tolerance check failed: {numeric_error}")

    offset, line, column = diff_location(expected_bytes, actual_bytes)
    expected_byte = expected_bytes[offset] if offset < len(expected_bytes) else None
    actual_byte = actual_bytes[offset] if offset < len(actual_bytes) else None
    context_start = max(0, offset - 40)
    context_end = offset + 40
    expected_context = expected_bytes[context_start:context_end].decode("utf-8", errors="replace")
    actual_context = actual_bytes[context_start:context_end].decode("utf-8", errors="replace")

    print(f"FAIL {case_id}")
    print(f"  first_diff_offset={offset} line={line} column={column}")
    print(f"  expected_byte={render_byte(expected_byte)}")
    print(f"  actual_byte={render_byte(actual_byte)}")
    print(f"  expected_sha256={sha256_bytes(expected_bytes)}")
    print(f"  actual_sha256={sha256_bytes(actual_bytes)}")
    print(f"  expected_path={expected_path}")
    print(f"  actual_path={actual_path}")
    print("  expected_context:")
    print(f"    {expected_context}")
    print("  actual_context:")
    print(f"    {actual_context}")
    return "fail"


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Compare actual exports against local expected baselines.")
    parser.add_argument(
        "--manifest",
        default=str(DEFAULT_MANIFEST),
        help="Path to baseline manifest JSON. Default: baseline/manifest.json",
    )
    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    manifest_path = Path(args.manifest).expanduser().resolve()
    manifest = load_manifest(manifest_path)
    cases = list(iter_enabled_cases(manifest))
    if not cases:
        print("No enabled cases in manifest.")
        return 1

    passed = 0
    failed = 0
    skipped = 0
    for case in cases:
        result = compare_case(case, manifest=manifest, manifest_path=manifest_path)
        if result == "pass":
            passed += 1
        elif result == "fail":
            failed += 1
        else:
            skipped += 1

    print(f"Summary: {passed} passed, {failed} failed, {skipped} skipped, {len(cases)} total")
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
