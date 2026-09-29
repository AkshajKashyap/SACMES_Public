"""Pure state for SACMES analysis progress and normalization requests."""


class FileProgress:
    """Track completion notifications independently for each analysis file."""

    def __init__(self, file_count: int, required_completions: int):
        self.required_completions = required_completions
        self._completion_counts = [0] * file_count

    def record_completion(self, file_number: int) -> bool:
        """Record one notification and report whether its 1-based file completed."""
        index = file_number - 1
        self._completion_counts[index] += 1
        if self._completion_counts[index] == self.required_completions:
            self._completion_counts[index] = 0
            return True
        return False


class NormalizationRequest:
    """Represent whether a requested normalization update is pending."""

    def __init__(self):
        self.waiting = False

    def request(self) -> None:
        self.waiting = True

    def complete(self) -> None:
        self.waiting = False
