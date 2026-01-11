"""
CoreTemp reader

Reads CPU package temperature from coretemp hwmon interface.
"""

import os
import glob
import time
from config import SmoothingConfig


class CoretempReader:
    """Read CPU package temperature from coretemp hwmon with exponential smoothing"""

    def __init__(self):
        """Initialize coretemp reader by finding the coretemp device"""
        self.temp_input_path = self._find_package_temp()
        if not self.temp_input_path:
            raise RuntimeError("Could not find coretemp package temperature sensor")

        # Smoothing state (1 second half-life)
        self.smoothed_temp = None
        self.last_read_time = None

    def _find_package_temp(self):
        """
        Find the hwmon path for CPU package temperature

        Returns:
            Path to temp_input file for package temperature, or None if not found
        """
        # Find all hwmon devices
        hwmon_dirs = glob.glob('/sys/class/hwmon/hwmon*')

        for hwmon_dir in hwmon_dirs:
            # Check if this is coretemp
            name_file = os.path.join(hwmon_dir, 'name')
            if os.path.exists(name_file):
                with open(name_file, 'r') as f:
                    name = f.read().strip()
                    if name == 'coretemp':
                        # Found coretemp, now find package temp
                        # Look for temp*_label files
                        label_files = glob.glob(os.path.join(hwmon_dir, 'temp*_label'))
                        for label_file in label_files:
                            with open(label_file, 'r') as f:
                                label = f.read().strip()
                                if 'Package id' in label:
                                    # Found it! Get corresponding temp*_input
                                    temp_num = os.path.basename(label_file).replace('temp', '').replace('_label', '')
                                    temp_input = os.path.join(hwmon_dir, f'temp{temp_num}_input')
                                    if os.path.exists(temp_input):
                                        return temp_input
        return None

    def read_temperature(self):
        """
        Read CPU package temperature with exponential smoothing

        Uses 1-second half-life exponential moving average to smooth
        out rapid fluctuations while maintaining responsiveness.

        Returns:
            Smoothed temperature in Celsius (float)
        """
        try:
            # Read raw temperature
            with open(self.temp_input_path, 'r') as f:
                millidegrees = int(f.read().strip())
                raw_temp = millidegrees / 1000.0

            current_time = time.time()

            # Initialize on first read
            if self.smoothed_temp is None:
                self.smoothed_temp = raw_temp
                self.last_read_time = current_time
                return self.smoothed_temp

            # Calculate time delta
            dt = current_time - self.last_read_time
            self.last_read_time = current_time

            # Exponential smoothing with configured half-life
            # alpha = 0.5^(dt/halflife) (fraction of old value to keep)
            alpha = pow(0.5, dt / SmoothingConfig.CORETEMP_HALFLIFE)
            self.smoothed_temp = alpha * self.smoothed_temp + (1 - alpha) * raw_temp

            return self.smoothed_temp

        except (IOError, ValueError) as e:
            raise RuntimeError(f"Failed to read temperature: {e}")
