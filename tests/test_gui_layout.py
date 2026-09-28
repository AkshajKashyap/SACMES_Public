from unittest import TestCase

from gui_layout import bounded_window_geometry


class BoundedWindowGeometryTest(TestCase):
    def test_oversized_window_is_capped_and_centered(self):
        geometry = bounded_window_geometry(2400, 1400, 1920, 1080)

        self.assertEqual(geometry, (1728, 918, 96, 81))

    def test_smaller_window_keeps_requested_size_and_is_centered(self):
        geometry = bounded_window_geometry(1200, 700, 1920, 1080)

        self.assertEqual(geometry, (1200, 700, 360, 190))

    def test_nonpositive_dimension_is_rejected(self):
        with self.assertRaises(ValueError):
            bounded_window_geometry(1200, 700, 0, 1080)
