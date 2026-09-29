import tempfile
from pathlib import Path
from unittest import TestCase

from data_io import (
    DataIOConfig,
    column_index_for_current,
    file_is_complete,
    make_file_name,
    read_data,
)
from sacmes_shared import Delimiter, ElectrodesMode, FileEncoding


def make_config(
    *,
    electrodes_mode=ElectrodesMode.MULTIPLE,
    file_encoding=FileEncoding.UTF_8,
    delimiter=Delimiter.COMMA,
    voltage_column_index=0,
    base_column_index_for_currents=1,
    columns_per_electrode=2,
):
    return DataIOConfig(
        file_name_pattern="<H><E>_<F>Hz__<N>.txt",
        electrodes_mode=electrodes_mode,
        handle_variable="E",
        file_encoding=file_encoding,
        delimiter=delimiter,
        voltage_column_index=voltage_column_index,
        base_column_index_for_currents=base_column_index_for_currents,
        columns_per_electrode=columns_per_electrode,
    )


class MakeFileNameTest(TestCase):
    def test_single_mode_always_uses_electrode_one(self):
        filename = make_file_name(make_config(electrodes_mode=ElectrodesMode.SINGLE), 12, 9, 30)

        self.assertEqual(filename, "E1_30Hz__12.txt")

    def test_multiple_mode_uses_requested_electrode(self):
        filename = make_file_name(make_config(), 12, 4, 30)

        self.assertEqual(filename, "E4_30Hz__12.txt")


class ColumnIndexForCurrentTest(TestCase):
    def test_single_mode_offsets_current_column_for_electrode(self):
        config = make_config(
            electrodes_mode=ElectrodesMode.SINGLE,
            base_column_index_for_currents=2,
            columns_per_electrode=3,
        )

        self.assertEqual(column_index_for_current(config, electrode=4), 11)

    def test_multiple_mode_keeps_base_current_column(self):
        config = make_config(base_column_index_for_currents=2, columns_per_electrode=3)

        self.assertEqual(column_index_for_current(config, electrode=9), 2)


class ReadDataTest(TestCase):
    def setUp(self):
        self.temporary_directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary_directory.cleanup)
        self.root = Path(self.temporary_directory.name)

    def write_file(self, name, contents, encoding="utf-8"):
        path = self.root / name
        path.write_text(contents, encoding=encoding)
        return path

    def test_comma_delimited_single_mode_uses_electrode_current_column(self):
        path = self.write_file(
            "comma.txt",
            "instrument export\n"
            "potential,e1,unused,e2,unused,e3\n"
            "0.10,0.000001,10,0.000002,20,0.0000035\n"
            "-0.20,0.000004,30,0.000005,40,-0.000002\n",
        )
        config = make_config(electrodes_mode=ElectrodesMode.SINGLE)

        potentials, currents, potential_to_current = read_data(config, str(path), electrode=3)

        self.assertEqual(potentials, [0.1, -0.2])
        self.assertEqual(currents, [3.5, -2.0])
        self.assertEqual(potential_to_current, {0.1: 3.5, -0.2: -2.0})

    def test_tab_delimited_utf8_data(self):
        path = self.write_file(
            "tab.txt",
            "potential\tcurrent\n0.25\t0.000003\n0.50\t-0.00000125\n",
        )
        config = make_config(delimiter=Delimiter.TAB)

        potentials, currents, potential_to_current = read_data(config, str(path), electrode=1)

        self.assertEqual(potentials, [0.25, 0.5])
        self.assertEqual(currents, [3.0, -1.25])
        self.assertEqual(potential_to_current, {0.25: 3.0, 0.5: -1.25})

    def test_utf16_data(self):
        path = self.write_file(
            "utf16.txt",
            "potential,current\n1.25,0.0000025\n1.50,0.000004\n",
            encoding="utf-16",
        )
        config = make_config(file_encoding=FileEncoding.UTF_16)

        potentials, currents, potential_to_current = read_data(config, str(path), electrode=1)

        self.assertEqual(potentials, [1.25, 1.5])
        self.assertEqual(currents, [2.5, 4.0])
        self.assertEqual(potential_to_current, {1.25: 2.5, 1.5: 4.0})

    def test_single_space_delimited_data(self):
        path = self.write_file(
            "space.txt",
            "potential current\n0.75 0.00000225\n1.00 -0.0000005\n",
        )
        config = make_config(delimiter=Delimiter.SPACE)

        potentials, currents, potential_to_current = read_data(config, str(path), electrode=1)

        self.assertEqual(potentials, [0.75, 1.0])
        self.assertEqual(currents, [2.25, -0.5])
        self.assertEqual(potential_to_current, {0.75: 2.25, 1.0: -0.5})

    def test_missing_file_raises_prefixed_file_not_found(self):
        missing_path = self.root / "missing.txt"

        with self.assertRaisesRegex(FileNotFoundError, "^read_data: file not found "):
            read_data(make_config(), str(missing_path), electrode=1)


class FileIsCompleteTest(TestCase):
    def test_nonexistent_file_is_not_complete(self):
        with tempfile.TemporaryDirectory() as temporary_directory:
            missing_path = Path(temporary_directory) / "missing.txt"

            self.assertFalse(file_is_complete(str(missing_path)))

    def test_closed_ordinary_file_is_complete(self):
        with tempfile.TemporaryDirectory() as temporary_directory:
            path = Path(temporary_directory) / "closed.txt"
            path.write_text("complete\n", encoding="utf-8")

            self.assertTrue(file_is_complete(str(path)))
