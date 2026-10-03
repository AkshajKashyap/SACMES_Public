"""Completed-file timeline state for Continuous Scan analyses."""

from typing import Callable, List


class ContinuousScanTimeline:
    """Own positionally paired completed-file and elapsed-time values."""

    def __init__(self) -> None:
        self.files: List[int] = []
        self.samples: List[float] = []

    def record(
        self,
        file_number: int,
        sample_for_completed_count: Callable[[int], float],
    ) -> bool:
        """Record a unique file and its sample, returning whether it was added."""
        if file_number in self.files:
            return False
        self.files.append(file_number)
        self.samples.append(sample_for_completed_count(len(self.files)))
        return True
