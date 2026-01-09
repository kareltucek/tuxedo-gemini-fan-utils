"""
Fan Controller interface

Interfaces with the fanctl binary to control fan speeds and read temperatures.
"""

import subprocess
import sys
import os
import re


class FanController:
    """Interface to Tuxedo fan hardware using fanctl binary"""

    def __init__(self, fanctl_path, test_mode=False):
        """
        Initialize fan controller

        Args:
            fanctl_path: Path to fanctl binary
            test_mode: If True, don't actually set fan speeds
        """
        self.fanctl_path = fanctl_path
        self.test_mode = test_mode

        # Check if fanctl exists
        if not os.path.exists(self.fanctl_path):
            print(f"ERROR: fanctl not found at {self.fanctl_path}", file=sys.stderr)
            print("Build it first: cd fan_control && make", file=sys.stderr)
            sys.exit(1)

    def _run_fanctl(self, *args):
        """
        Run fanctl command and return output

        Args:
            *args: Command arguments to pass to fanctl

        Returns:
            Command output as string

        Raises:
            SystemExit on error
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
            print(f"ERROR running fanctl: {e}", file=sys.stderr)
            print(f"Output: {e.stdout}", file=sys.stderr)
            print(f"Error: {e.stderr}", file=sys.stderr)
            sys.exit(1)
        except PermissionError:
            print(f"ERROR: Permission denied running {self.fanctl_path}", file=sys.stderr)
            print("Must run as root: sudo python3 fan-pid-control.py", file=sys.stderr)
            sys.exit(1)

    def read_fan_info(self, fan_num):
        """
        Read fan information using fanctl status

        Args:
            fan_num: Fan number (0 or 1)

        Returns:
            Tuple of (speed_pct, temp1, temp2)
                speed_pct: Current fan speed percentage
                temp1: Temperature sensor 1 (°C)
                temp2: Temperature sensor 2 (°C)
        """
        output = self._run_fanctl('status')

        # Parse output looking for fan info
        # Example line: "  Speed: 35.3% (raw: 90/255)"
        # Example line: "  Temp2: 66°C"

        lines = output.split('\n')
        in_fan_section = False
        speed_pct = 0
        temp1 = 0
        temp2 = 0

        for line in lines:
            if f'Fan {fan_num}' in line:
                in_fan_section = True
                continue

            if in_fan_section:
                if line.strip() == '':
                    break

                # Parse speed line
                match = re.search(r'Speed:\s+([\d.]+)%', line)
                if match:
                    speed_pct = float(match.group(1))

                # Parse temp1 line
                match = re.search(r'Temp1:\s+(\d+)°C', line)
                if match:
                    temp1 = int(match.group(1))

                # Parse temp2 line
                match = re.search(r'Temp2:\s+(\d+)°C', line)
                if match:
                    temp2 = int(match.group(1))

        return speed_pct, temp1, temp2

    def set_fan_speed(self, fan_num, speed_pct):
        """
        Set fan speed using fanctl

        Args:
            fan_num: Fan number (0 or 1)
            speed_pct: Speed percentage (0-100)
        """
        if self.test_mode:
            # In test mode, don't actually set the speed
            return

        self._run_fanctl('set', str(fan_num), str(int(speed_pct)))

    def set_auto_mode(self):
        """Return fans to automatic control"""
        if self.test_mode:
            return

        self._run_fanctl('auto')
