"""Small, display-independent helpers for sizing the SACMES GUI."""

from typing import Tuple


WINDOW_WIDTH_FRACTION = 0.90
WINDOW_HEIGHT_FRACTION = 0.85


def bounded_window_geometry(
    requested_width: int,
    requested_height: int,
    screen_width: int,
    screen_height: int,
) -> Tuple[int, int, int, int]:
    """Return a centered geometry that leaves room for window decorations."""
    if min(requested_width, requested_height, screen_width, screen_height) <= 0:
        raise ValueError("window and screen dimensions must be positive")

    maximum_width = max(1, int(screen_width * WINDOW_WIDTH_FRACTION))
    maximum_height = max(1, int(screen_height * WINDOW_HEIGHT_FRACTION))
    width = min(requested_width, maximum_width)
    height = min(requested_height, maximum_height)
    x_position = max(0, (screen_width - width) // 2)
    y_position = max(0, (screen_height - height) // 2)
    return width, height, x_position, y_position


def fit_window_to_screen(window) -> None:
    """Cap a Tk top-level's requested size and center it on the screen."""
    window.update_idletasks()
    width, height, x_position, y_position = bounded_window_geometry(
        window.winfo_reqwidth(),
        window.winfo_reqheight(),
        window.winfo_screenwidth(),
        window.winfo_screenheight(),
    )
    window.geometry(f"{width}x{height}+{x_position}+{y_position}")
