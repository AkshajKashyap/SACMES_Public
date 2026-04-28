"""Text file export support for SACMES."""

from __future__ import annotations

import csv
from dataclasses import dataclass
import time
from math import sqrt
from typing import Any, Dict, List, Optional

from sacmes_shared import AnalysisMethod, HighLow, PeakMethod, PlotSummaryMode


_RUNTIME_MODULE: Any = None


def set_runtime_module(module: Any) -> None:
    global _RUNTIME_MODULE
    _RUNTIME_MODULE = module


def _runtime() -> Any:
    if _RUNTIME_MODULE is None:
        raise RuntimeError("TextFileExport runtime module has not been configured.")
    return _RUNTIME_MODULE


@dataclass(frozen=True)
class ExportSnapshot:
    export_file_path: str
    analysis_method: AnalysisMethod
    plot_summary_mode: PlotSummaryMode
    peak_method: PeakMethod
    electrode_list: List[int]
    electrode_count: int
    frequency_list: List[int]
    global_electrode_count: int
    global_frequency_list: List[int]
    frequency_dict: Dict[int, int]
    frame_list: List[str]
    sample_list: List[float]
    data_list: Any
    peak_list: Any
    high_low_dictionary: Dict[HighLow, int]
    normalized_data_list: Any
    offset_normalized_data_list: Any
    normalized_ratiometric_data_list: Any
    kdm_list: Any


def _build_continuous_scan_peak_method_row(snapshot: ExportSnapshot) -> Optional[List[str]]:
    match snapshot.plot_summary_mode:
        case PlotSummaryMode.PHE:
            txt_list: List[str] = []
            match snapshot.peak_method:
                case PeakMethod.POLY:
                    txt_list.append("Peak Method: Poly Fit")
                case PeakMethod.GAUSS:
                    txt_list.append("Peak Method: Gauss")
            return txt_list
    return None


def _build_continuous_scan_header_row(snapshot: ExportSnapshot) -> List[str]:
    txt_list: List[str] = []
    txt_list.append("File")
    txt_list.append("Time(Hrs)")
    for frequency in snapshot.frequency_list:
        for electrode in snapshot.electrode_list:
            match snapshot.plot_summary_mode:
                case PlotSummaryMode.PHE:
                    txt_list.append("PeakHeight_E%d_%dHz" % (electrode, frequency))
                    match snapshot.peak_method:
                        case PeakMethod.GAUSS:
                            txt_list.append("PeakLocation_E%d_%dHz" % (electrode, frequency))
                case PlotSummaryMode.AUC:
                    txt_list.append("AUC_E%d_%dHz" % (electrode, frequency))
    if snapshot.electrode_count > 1:
        for frequency in snapshot.frequency_list:
            match snapshot.plot_summary_mode:
                case PlotSummaryMode.PHE:
                    txt_list.append("Avg_PeakHeight_%dHz" % frequency)
                case PlotSummaryMode.AUC:
                    txt_list.append("Avg_AUC_%dHz" % frequency)
    for frequency in snapshot.frequency_list:
        for electrode in snapshot.electrode_list:
            txt_list.append(f"Norm_E{electrode}_{frequency}Hz")
    if snapshot.electrode_count > 1:
        for frequency in snapshot.frequency_list:
            txt_list.append(f"Average_Norm_{frequency}Hz")
        for frequency in snapshot.frequency_list:
            txt_list.append(f"SD_Norm_{frequency}Hz")
    if len(snapshot.frequency_list) > 1:
        for electrode in snapshot.electrode_list:
            txt_list.append(f"NormalizedRatio_E{electrode}")
        if snapshot.electrode_count > 1:
            txt_list.append("NormalizedRatioAvg")
            txt_list.append("NormalizedRatioSTD")
        for electrode in snapshot.electrode_list:
            txt_list.append(f"KDM_E{electrode}")
        if snapshot.electrode_count > 1:
            txt_list.append("AvgKDM")
            txt_list.append("KDM_STD")
    return txt_list


def _build_frequency_map_header_row(snapshot: ExportSnapshot) -> List[str]:
    txt_list = []
    txt_list.append("Frequency(Hz)")
    e_count = 1
    for _ in snapshot.frame_list:
        match snapshot.plot_summary_mode:
            case PlotSummaryMode.PHE:
                txt_list.append(f"PeakHeight_E{e_count}(µA)")
            case PlotSummaryMode.AUC:
                txt_list.append(f"AUC_E{e_count}")
        txt_list.append(f"Charge_E{e_count}(µC)")
        e_count += 1
    if snapshot.electrode_count > 1:
        txt_list.append("Avg.PeakHeight(µA)")
        txt_list.append("Standard_Deviation(µA)")
        txt_list.append("Avg.Charge(µC)")
        txt_list.append("Standard_Deviation(µC)")
    return txt_list


def _build_continuous_scan_export_row(snapshot: ExportSnapshot, file: int) -> List[str]:
    normalized_frequency_currents: List[float]
    norm_list: List[float]
    kdm_list: List[float]
    running_sum: float
    average: float
    average_norm: float
    index: int = file - 1
    output_list: List[str] = []
    output_list.append(str(file))
    output_list.append(str(snapshot.sample_list[index]))
    #--- Peak Height ---#
    for count in range(len(snapshot.global_frequency_list)):
        for num in range(snapshot.global_electrode_count):
            output_list.append(str(snapshot.data_list[num][count][index]))
            match snapshot.peak_method:
                case PeakMethod.GAUSS:
                    output_list.append(str(snapshot.peak_list[num][count][index]))
    #--- Avg. Peak Height ---#
    if snapshot.electrode_count > 1:
        for count in range(len(snapshot.global_frequency_list)):
            running_sum = 0
            for num in range(snapshot.global_electrode_count):
                running_sum += snapshot.data_list[num][count][index]
            average = running_sum/snapshot.global_electrode_count
            output_list.append(str(average))
    #--- Peak Height/AUC Data Normalization ---#
    for count in range(len(snapshot.global_frequency_list)):
        for num in range(snapshot.global_electrode_count):
            if snapshot.global_frequency_list[count] == snapshot.high_low_dictionary[HighLow.LOW]:
                output_list.append(str(snapshot.offset_normalized_data_list[num][index]))
            else:
                output_list.append(str(snapshot.normalized_data_list[num][count][index]))
    #--- Average normalized data across all electrodes for each frequency ---#
    if snapshot.electrode_count > 1:
        for count in range(len(snapshot.global_frequency_list)):
            normalized_frequency_currents = []
            for num in range(snapshot.global_electrode_count):
                if snapshot.global_frequency_list[count] == snapshot.high_low_dictionary[HighLow.LOW]:
                    normalized_frequency_currents.append(snapshot.offset_normalized_data_list[num][index])
                else:
                    normalized_frequency_currents.append(snapshot.normalized_data_list[num][count][index])
            average_norm = sum(normalized_frequency_currents)/snapshot.global_electrode_count
            output_list.append(str(average_norm))
    #--- Standard Deviation ---#
    if snapshot.electrode_count > 1:
        for count in range(len(snapshot.global_frequency_list)):
            normalized_frequency_currents = []
            for num in range(snapshot.global_electrode_count):
                normalized_frequency_currents.append(snapshot.normalized_data_list[num][count][index])
            average_norm = sum(normalized_frequency_currents)/snapshot.global_electrode_count
            std_list = [(x - average_norm)**2 for x in normalized_frequency_currents]
            standard_deviation = float(sqrt(sum(std_list)/(snapshot.global_electrode_count - 1)))
            output_list.append(str(standard_deviation))
    if len(snapshot.global_frequency_list) > 1:
        #--- Append Normalized Ratiometric Data ---#
        norm_list = []
        for num in range(snapshot.global_electrode_count):
            output_list.append(str(snapshot.normalized_ratiometric_data_list[num][index]))
            norm_list.append(snapshot.normalized_ratiometric_data_list[num][index])
        if snapshot.electrode_count > 1:
            norm_average: float = sum(norm_list)/snapshot.global_electrode_count
            output_list.append(str(norm_average))
            norm_std_list: List[float] = [(x - norm_average)**2 for x in norm_list]
            norm_standard_deviation = sqrt(sum(norm_std_list)/(snapshot.global_electrode_count - 1))
            output_list.append(str(norm_standard_deviation))
        #--- Append KDM ---#
        kdm_list = []
        for num in range(snapshot.global_electrode_count):
            output_list.append(str(snapshot.kdm_list[num][index]))
            kdm_list.append(snapshot.kdm_list[num][index])
        if snapshot.electrode_count > 1:
            kdm_average: float = sum(kdm_list)/snapshot.global_electrode_count
            output_list.append(str(kdm_average))
            kdm_std_list: List[float] = [(x - kdm_average)**2 for x in kdm_list]
            kdm_std: float = sqrt(sum(kdm_std_list)/(snapshot.global_electrode_count - 1))
            output_list.append(str(kdm_std))
    return output_list


class TextFileExport():
    """Class for exporting data to a .txt file."""
    def __init__(self,\
                 electrodes: Optional[List[int]] = None,\
                 frequencies: Optional[List[int]] = None):
        #declarations for fields that will be initialized in other methods
        self.electrode_list: List[int]
        self.electrode_count: int
        self.frequency_list: List[int]
        self.text_file_handle: str

    def initialize(self,\
                 electrodes: Optional[List[int]] = None,\
                 frequencies: Optional[List[int]] = None,
                 snapshot: Optional[ExportSnapshot] = None):
        if snapshot is None:
            snapshot = _runtime().text_export_snapshot(electrodes=electrodes,\
                                                       frequencies=frequencies)
        self.electrode_list = snapshot.electrode_list
        self.electrode_count = len(self.electrode_list)
        self.frequency_list = snapshot.frequency_list
        self.text_file_handle = snapshot.export_file_path
        match snapshot.analysis_method:
            case AnalysisMethod.CONTINUOUS_SCAN:
                peak_method_row = _build_continuous_scan_peak_method_row(snapshot)
                if peak_method_row is not None:
                    with open(self.text_file_handle, "w+", encoding="utf-8", newline="") as output:
                        writer = csv.writer(output, delimiter=" ")
                        writer.writerow(peak_method_row)
                txt_list = _build_continuous_scan_header_row(snapshot)
                with open(self.text_file_handle, "a", encoding="utf-8", newline="") as output:
                    writer = csv.writer(output, delimiter=" ")
                    writer.writerow(txt_list)
            case AnalysisMethod.FREQUENCY_MAP:
                txt_list = _build_frequency_map_header_row(snapshot)
                with open(self.text_file_handle, "w+", encoding="utf-8", newline="") as output:
                    writer = csv.writer(output, delimiter=" ")
                    writer.writerow(txt_list)
        return self

    def continuous_scan_export(self, file: int, snapshot: ExportSnapshot) -> None:
        """Export the data from the current file."""
        output_list = _build_continuous_scan_export_row(snapshot, file)
        #--- Write the data into the .txt file ---#
        with open(self.text_file_handle, "a", encoding="utf-8", newline="") as text_io_wrapper:
            writer = csv.writer(text_io_wrapper, delimiter=" ")
            writer.writerow(output_list)
        with open(self.text_file_handle, "r", encoding="utf-8", newline="") as filecontents:
            filedata = filecontents.read()
        filedata = filedata.replace("[", "")
        filedata = filedata.replace("\"", "")
        filedata = filedata.replace("]", "")
        filedata = filedata.replace(",", "")
        filedata = filedata.replace("'", "")
        with open(self.text_file_handle, "w", encoding="utf-8", newline="") as output:
            output.write(filedata)

    def frequency_map_export(self, file: int, frequency: int, snapshot: ExportSnapshot) -> None:
        """Export the data from the current file."""
        output_list: List[str] = []
        index: int = file - 1
        running_sum: float
        average: float
        try:
            output_list.append(str(frequency))
            count = snapshot.frequency_dict[frequency]
            # Peak Height / AUC
            for num in range(snapshot.global_electrode_count):
                output_list.append(str(snapshot.data_list[num][count][index]))
                output_list.append(str(snapshot.data_list[num][count][index]/frequency))
            # Average Peak Height / AUC
            if self.electrode_count > 1:
                running_sum = 0
                for num in range(snapshot.global_electrode_count):
                    running_sum += snapshot.data_list[num][count][index]
                average = running_sum/snapshot.global_electrode_count
                output_list.append(str(average))
                # Standard Deviation of a Sample across all electrodes
                # for Peak Height/AUC
                std_list: List[float] = []
                for num in range(snapshot.global_electrode_count):
                    std_list.append(snapshot.data_list[num][count][index])
                std_list = [(value - average)**2 for value in std_list]
                standard_deviation = sqrt(sum(std_list)/(snapshot.global_electrode_count - 1))
                output_list.append(str(standard_deviation))
                #-- Average Charge --#
                avg_charge = average/frequency
                output_list.append(str(avg_charge))
                #-- Charge STD --#
                std_list = []
                for num in range(snapshot.global_electrode_count):
                    std_list.append(snapshot.data_list[num][count][index])
                std_list = [x/frequency for x in std_list]
                std_list = [(value - avg_charge)**2 for value in std_list]
                charge_standard_deviation = sqrt(sum(std_list)/(snapshot.global_electrode_count - 1))
                output_list.append(str(charge_standard_deviation))
            #--- Write the data into the .txt file ---#
            with open(self.text_file_handle, "a", encoding="utf-8", newline="") as output:
                writer = csv.writer(output, delimiter=" ")
                writer.writerow(output_list)
            with open(self.text_file_handle, "r", encoding="utf-8", newline="") as filecontents:
                filedata = filecontents.read()
            filedata = filedata.replace("[", "")
            filedata = filedata.replace("\"", "")
            filedata = filedata.replace("]", "")
            filedata = filedata.replace(",", "")
            filedata = filedata.replace("'", "")
            with open(self.text_file_handle, "w", encoding="utf-8", newline="") as output:
                output.write(filedata)
        except Exception as exception:
            print("Error in frequency_map_export", exception)
            time.sleep(3)

    def txt_file_normalization(self) -> None:
        """Normalize the data within the text file."""
        runtime = _runtime()
        try:
            #--- reinitialize the .txt file ---#
            self.initialize(electrodes=self.electrode_list, frequencies=self.frequency_list)
            #--- rewrite the data for the files that have already been analyzed and normalize
            # them to the new standard---#
            if runtime.global_analysis_complete:
                analysis_range = len(runtime.global_file_list)
            else:
                analysis_range = len(runtime.global_file_list) - 1
            for index in range(analysis_range):
                file: int = index + 1
                txt_list: List[str] = []
                #AvgList = [] #not used
                txt_list.append(str(file))
                txt_list.append(str(runtime.global_sample_list[index]))
                #--- peak height ---#
                for frequency in self.frequency_list:
                    count = runtime.global_frequency_dict[frequency]
                    for electrode in self.electrode_list:
                        num = runtime.global_electrode_dict[electrode]
                        txt_list.append(str(runtime.global_data_list[num][count][index]))
                        match runtime.global_peak_method:
                            case PeakMethod.GAUSS:
                                txt_list.append(str(runtime.global_peak_list[num][count][index]))
                #--- Avg. Peak Height ---#
                if self.electrode_count > 1:
                    for frequency in self.frequency_list:
                        count = runtime.global_frequency_dict[frequency]
                        running_sum: float = 0
                        for electrode in self.electrode_list:
                            num = runtime.global_electrode_dict[electrode]
                            running_sum += runtime.global_data_list[num][count][index]
                        average = running_sum/self.electrode_count
                        txt_list.append(str(average))
                #--- Data Normalization ---#
                for frequency in self.frequency_list:
                    count = runtime.global_frequency_dict[frequency]
                    normalized_frequency_currents: List[float] = []
                    for electrode in self.electrode_list:
                        num = runtime.global_electrode_dict[electrode]
                        if frequency == runtime.global_high_low_dictionary[HighLow.LOW]:
                            txt_list.append(str(runtime.global_offset_normalized_data_list[num][index]))
                        else:
                            txt_list.append(str(runtime.global_normalized_data_list[num][count][index]))
                #--- Average Data Normalization ---#
                if self.electrode_count > 1:
                    for frequency in self.frequency_list:
                        count = runtime.global_frequency_dict[frequency]
                        normalized_frequency_currents = []
                        for electrode in self.electrode_list:
                            num = runtime.global_electrode_dict[electrode]
                            if frequency == runtime.global_high_low_dictionary[HighLow.LOW]:
                                normalized_frequency_currents.append(runtime.global_offset_normalized_data_list[num][index])
                            else:
                                normalized_frequency_currents.append(runtime.global_normalized_data_list[num][count][index])
                        average_norm = sum(normalized_frequency_currents)/self.electrode_count
                        txt_list.append(str(average_norm))
                    #--- Standard Deviation between electrodes ---#
                    for frequency in self.frequency_list:
                        count = runtime.global_frequency_dict[frequency]
                        normalized_frequency_currents = []
                        for electrode in self.electrode_list:
                            num = runtime.global_electrode_dict[electrode]
                            if frequency == runtime.global_high_low_dictionary[HighLow.LOW]:
                                normalized_frequency_currents.append(runtime.global_offset_normalized_data_list[num][index])
                            else:
                                normalized_frequency_currents.append(runtime.global_normalized_data_list[num][count][index])
                        average_norm = sum(normalized_frequency_currents)/self.electrode_count
                        std_list = [(x - average_norm)**2 for x in normalized_frequency_currents]
                        standard_deviation = sqrt(sum(std_list)/(self.electrode_count - 1))
                        txt_list.append(str(standard_deviation))
                if len(self.frequency_list) > 1:
                    #--- Append Normalized Ratiometric Data ---#
                    norm_list: List[float] = []
                    for electrode in self.electrode_list:
                        num = runtime.global_electrode_dict[electrode]
                        txt_list.append(str(runtime.global_normalized_ratiometric_data_list[num][index]))
                        norm_list.append(runtime.global_normalized_ratiometric_data_list[num][index])
                    if self.electrode_count > 1:
                        norm_average = sum(norm_list)/self.electrode_count
                        txt_list.append(str(norm_average))
                        norm_std_list = [(x - norm_average)**2 for x in norm_list]
                        norm_standard_deviation = sqrt(sum(norm_std_list)/(self.electrode_count-1))
                        txt_list.append(str(norm_standard_deviation))
                    #--- Append KDM ---#
                    kdm_list = []
                    for electrode in self.electrode_list:
                        num = runtime.global_electrode_dict[electrode]
                        txt_list.append(str(runtime.global_kdm_list[num][index]))
                        kdm_list.append(runtime.global_kdm_list[num][index])
                    if self.electrode_count > 1:
                        kdm_average: float = sum(kdm_list)/self.electrode_count
                        txt_list.append(str(kdm_average))
                        kdm_std_list: List[float] = [(x - kdm_average)**2 for x in kdm_list]
                        kdm_std: float = sqrt(sum(kdm_std_list)/(self.electrode_count - 1))
                        txt_list.append(str(kdm_std))
                #--- Write the data into the .txt file ---#
                with open(self.text_file_handle, "a", encoding="utf-8", newline="") as output:
                    writer = csv.writer(output, delimiter=" ")
                    writer.writerow(txt_list)
                with open(self.text_file_handle, "r", encoding="utf-8", newline="") as filecontents:
                    filedata = filecontents.read()
                filedata = filedata.replace("[", "")
                filedata = filedata.replace("\"", "")
                filedata = filedata.replace("]", "")
                filedata = filedata.replace(",", "")
                filedata = filedata.replace("'", "")
                with open(self.text_file_handle, "w", encoding="utf-8", newline="") as output:
                    output.write(filedata)
            try:
                from scripts import baseline_capture
                baseline_capture.capture_export_rewrite({
                    "dataset_path": runtime.global_file_path,
                    "export_path": self.text_file_handle,
                    "analysis_method": str(runtime.global_analysis_method),
                    "electrode_list": list(self.electrode_list),
                    "frequency_list": list(self.frequency_list),
                    "normalization_point": runtime.global_normalization_point,
                    "global_analysis_complete": runtime.global_analysis_complete,
                    "file_list": list(runtime.global_file_list),
                    "sample_list": list(runtime.global_sample_list),
                    "normalized_data_list": runtime.global_normalized_data_list,
                    "offset_normalized_data_list": runtime.global_offset_normalized_data_list,
                    "normalized_ratiometric_data_list": runtime.global_normalized_ratiometric_data_list,
                    "kdm_list": runtime.global_kdm_list,
                })
            except Exception as exception:
                print("Baseline capture skipped in txt_file_normalization", exception)
        except Exception as exception:
            print("Error in txt_file_normalization", exception)
            time.sleep(0.1)
