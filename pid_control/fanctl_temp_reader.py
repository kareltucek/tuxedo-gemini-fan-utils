"""
Fanctl temperature reader

Reads temperature sensors via fanctl binary.
"""

import subprocess
import re
import time
from config import SmoothingConfig


class FanctlTempReader:
    """Read temperatures from fanctl status output with exponential smoothing"""

    def __init__(self, fanctl_path):
        """
        Initialize fanctl temperature reader

        Args:
            fanctl_path: Path to fanctl binary
        """
        self.fanctl_path = fanctl_path

        # Smoothing state
        self.smoothed_max_temp = None
        self.last_read_time = None

    def _run_fanctl(self, *args):
        """
        Run fanctl command and return output

        Args:
            *args: Command arguments

        Returns:
            Command output as string
        """
        try:
            result = subprocess.run(
                [self.fanctl_path] + list(args),
                capture_output=True,
                text=True,
                check=True
            )
            return result.stdout
        except subprocess.CalledProcessError as e:
            raise RuntimeError(f"fanctl command failed: {e.stderr}")

    def read_temperatures(self):
        """
        Read all fan temperatures from fanctl

        Returns:
            List of temperatures from available fans
            Only returns Temp2 values (more reliable sensor)
        """
        output = self._run_fanctl('status')
        temperatures = []

        # Parse each fan block
        for line in output.split('\n'):
            # Look for Temp2 readings
            match = re.search(r'Temp2:\s+(\d+)°C', line)
            if match:
                temp = int(match.group(1))
                # Only include valid readings (> 1°C means sensor exists)
                if temp > 1:
                    temperatures.append(float(temp))

        return temperatures

    def read_max_temperature(self):
        """
        Read maximum temperature across all fanctl sensors with exponential smoothing

        Returns:
            Smoothed maximum temperature in Celsius
        """
        temps = self.read_temperatures()
        if not temps:
            raise RuntimeError("No valid temperature readings from fanctl")

        raw_max_temp = max(temps)
        current_time = time.time()

        # Initialize on first read
        if self.smoothed_max_temp is None:
            self.smoothed_max_temp = raw_max_temp
            self.last_read_time = current_time
            return self.smoothed_max_temp

        # Calculate time delta
        dt = current_time - self.last_read_time
        self.last_read_time = current_time

        # Exponential smoothing with configured half-life
        alpha = pow(0.5, dt / SmoothingConfig.FANCTL_TEMP_HALFLIFE)
        self.smoothed_max_temp = alpha * self.smoothed_max_temp + (1 - alpha) * raw_max_temp

        return self.smoothed_max_temp
