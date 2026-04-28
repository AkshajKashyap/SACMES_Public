"""Data-file naming and reading helpers for SACMES."""

from __future__ import annotations

import os
from typing import Any, Dict, List, Tuple

match os.name:
    case 'posix': # Linux/MacOS
        import fcntl
    case 'nt': # Windows
        import msvcrt

from sacmes_shared import ElectrodesMode


_RUNTIME_MODULE: Any = None


def set_runtime_module(module: Any) -> None:
    global _RUNTIME_MODULE
    _RUNTIME_MODULE = module


def _runtime() -> Any:
    if _RUNTIME_MODULE is None:
        raise RuntimeError("Data IO runtime module has not been configured.")
    return _RUNTIME_MODULE


def file_is_complete(filename: str) -> bool:
    """Heuristic test if the file is complete in the sense
    that the data acquisition software is no longer writing
    the file. In the original SACMES code, this heuristic was
    based on file length, which is not reliable; indeed it is
    wrong in the normal mode of operation.
    In the new implementation, one we know the file exists
    we check if it is open by any running process. If not,
    we consider that it is complete."""
    #return os.path.exists(filename) and os.path.getsize(filename) > global_byte_limit
    #return True
    #Trying a new method since psutil.process_iter() takes a long time.
    if os.path.exists(filename):
        match os.name:
            case 'posix': # Linux/MacOS
                try:
                    with open(filename, 'r+') as f:
                        fcntl.flock(f, fcntl.LOCK_EX | fcntl.LOCK_NB)  # Try locking the file
                        fcntl.flock(f, fcntl.LOCK_UN)  # Unlock immediately
                    return True  # Locking succeeded, file is not in use
                except IOError:
                    return False # File is locked, wait and retry\
            case 'nt': # Windows
                try:
                    with open(filename, 'r+') as f:
                        msvcrt.locking(f.fileno(), msvcrt.LK_NBLCK, 1)  # Try locking the file
                        msvcrt.locking(f.fileno(), msvcrt.LK_UNLCK, 1)  # Unlock immediately
                    return True  # Locking succeeded, file is not in use
                except OSError:
                    return False # File is locked, wait and retry\
        # for proc in psutil.process_iter():
        #     print("STILL SEARCHING PROCESSES")
        #     try:
        #         for file in proc.open_files():
        #             if file.path == filename:
        #                 #print(f"{filename} open by {proc.pid}")
        #                 return False
        #     except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
        #         pass
        # #print(f"{filename} assumed not open; length={os.path.getsize(filename)}")
        # return True
    else:
        #print(f"{filename} does not exist")
        return False


def make_file_name(file_index: int, electrode: int, frequency: int) -> str:
    """Instantiate the file name pattern with the given values."""
    runtime = _runtime()
    name: str = runtime.global_file_name_pattern
    match runtime.global_electrodes_mode:
        case ElectrodesMode.SINGLE:
            name = name.replace("<H>", runtime.global_handle_variable)
            name = name.replace("<E>", "1")
            name = name.replace("<F>", str(frequency))
            name = name.replace("<N>", str(file_index))
        case ElectrodesMode.MULTIPLE:
            name = name.replace("<H>", runtime.global_handle_variable)
            name = name.replace("<E>", str(electrode))
            name = name.replace("<F>", str(frequency))
            name = name.replace("<N>", str(file_index))
    return name


def read_data(input_file_name: str, electrode: int) ->\
    Tuple[List[float], List[float], Dict[float, float]]:
    """Extract numerical data for potentials and currents
    from an instrument-produced data file,
    and return them as a tuple
    (potentials, currents, potential_to_current_map).
    """
    runtime = _runtime()
    potentials: List[float]
    currents: List[float]
    potential_to_current_map: Dict[float, float]
    try:
        with open(input_file_name, "r", encoding=str(runtime.global_file_encoding)) as mydata:
            potentials = []
            currents = []
            potential_to_current_map = {}
            for line in mydata:
                check_split_list = line.split(str(runtime.global_delimiter))
                while check_split_list[0] == " " or check_split_list[0] == "\t":
                    del check_split_list[0]
                check_split_first_item: str = check_split_list[0].replace(",", "")
                first_item_is_float: bool
                try:
                    float(check_split_first_item)
                    first_item_is_float = True
                except ValueError:
                    first_item_is_float = False
                if first_item_is_float:
                    current_value: float =\
                        1000000 * float(check_split_list[column_index_for_current(electrode)].\
                                        replace(",", ""))
                    currents.append(current_value)
                    potential_value: float =\
                        float(line.split(str(runtime.global_delimiter))[runtime.global_voltage_column_index].\
                              strip(","))
                    potentials.append(potential_value)
                    potential_to_current_map[potential_value] = current_value
        return potentials, currents, potential_to_current_map
    except FileNotFoundError as exception:
        runtime.internal_error("read_data: file not found " + str(exception))


#######################################
### Retrieve the column index value ###
#######################################
def column_index_for_current(electrode: int) -> int:
    """Depending on the type of instrument output file
    (single file for all electrodes, or multiple files),
    guess the column with the data for the given electrode.
    """
    runtime = _runtime()
    match runtime.global_electrodes_mode:
        case ElectrodesMode.SINGLE:
            return runtime.global_base_column_index_for_currents +\
                  (electrode-1)*runtime.global_columns_per_electrode
        case ElectrodesMode.MULTIPLE:
            return runtime.global_base_column_index_for_currents
