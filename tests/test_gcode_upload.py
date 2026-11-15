import unittest

from simulation_main import _prepare_upload_gcode


class GcodeUploadTests(unittest.TestCase):
    def test_prepares_printer_specific_temperatures_and_removes_zero_commands(self):
        source = (
            b"M104 S205\n"
            b"M109 S220 ; wait for nozzle\n"
            b"M104 S0 ; nozzle off\n"
            b"M104 S0.0\n"
            b"M109 S0 ; do not change zero target\n"
            b"M140 S0\n"
            b"M140 S0.0 ; bed off\n"
            b"M140 S60\n"
            b"; M104 S99\n"
            b"G1 X10 Y20\n"
        )

        printer_1 = _prepare_upload_gcode(source, 1)
        printer_2 = _prepare_upload_gcode(source, 2)

        self.assertEqual(
            printer_1,
            b"M104 S210\n"
            b"M109 S210 ; wait for nozzle\n"
            b"M109 S0 ; do not change zero target\n"
            b"M140 S60\n"
            b"; M104 S99\n"
            b"G1 X10 Y20\n",
        )
        self.assertEqual(
            printer_2,
            b"M104 S230\n"
            b"M109 S230 ; wait for nozzle\n"
            b"M109 S0 ; do not change zero target\n"
            b"M140 S60\n"
            b"; M104 S99\n"
            b"G1 X10 Y20\n",
        )
        self.assertIn(b"M104 S0 ; nozzle off\n", source)
        self.assertIn(b"M140 S0\n", source)

    def test_rejects_unknown_printer_id(self):
        with self.assertRaisesRegex(ValueError, "Unsupported printer ID"):
            _prepare_upload_gcode(b"M104 S200\n", 3)


if __name__ == "__main__":
    unittest.main()
