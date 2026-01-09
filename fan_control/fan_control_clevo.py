#!/usr/bin/env python3
"""
Tuxedo Gemini Gen2 Fan Control Utility (Clevo Interface)

Direct fan control for Tuxedo laptops using the /dev/tuxedo_io Clevo interface.
For Gemini Gen2 and other Clevo-based Tuxedo devices.

Requires root privileges to access /dev/tuxedo_io
WARNING: Stop tccd service before using this to avoid conflicts
"""

import fcntl
import struct
import sys
import argparse
import subprocess

# Device file
DEVICE = '/dev/tuxedo_io'

# ioctl magic numbers
IOCTL_MAGIC = 0xEC
MAGIC_READ_CL = IOCTL_MAGIC + 1   # Clevo read
MAGIC_WRITE_CL = IOCTL_MAGIC + 2  # Clevo write

# Helper functions to create ioctl command numbers
def _IOR(magic, nr):
    """Create ioctl read command number"""
    return 0x80000000 | (4 << 16) | (magic << 8) | nr

def _IOW(magic, nr):
    """Create ioctl write command number"""
    return 0x40000000 | (4 << 16) | (magic << 8) | nr

# Clevo interface ioctl commands
R_CL_FANINFO1 = _IOR(MAGIC_READ_CL, 0x10)  # Read fan 1 info (CPU)
R_CL_FANINFO2 = _IOR(MAGIC_READ_CL, 0x11)  # Read fan 2 info (GPU)
R_CL_FANINFO3 = _IOR(MAGIC_READ_CL, 0x12)  # Read fan 3 info (GPU2)

W_CL_FANSPEED = _IOW(MAGIC_WRITE_CL, 0x10)  # Set all fan speeds
W_CL_FANAUTO = _IOW(MAGIC_WRITE_CL, 0x11)   # Return to automatic control

# Max fan speed for Clevo devices (255 = 100%)
MAX_FAN_SPEED = 255


def check_tccd_running():
    """Check if tccd service is running"""
    try:
        result = subprocess.run(['pgrep', '-f', 'tccd'], capture_output=True)
        return result.returncode == 0
    except:
        return False


class TuxedoFanControlClevo:
    """Interface to Tuxedo fan control via /dev/tuxedo_io (Clevo interface)"""

    def __init__(self, device_path=DEVICE):
        self.device_path = device_path
        self.dev = None

    def __enter__(self):
        try:
            self.dev = open(self.device_path, 'rb+', buffering=0)
        except PermissionError:
            print(f"ERROR: Permission denied accessing {self.device_path}", file=sys.stderr)
            print("This utility requires root privileges. Try: sudo python3 fan_control_clevo.py", file=sys.stderr)
            sys.exit(1)
        except FileNotFoundError:
            print(f"ERROR: Device {self.device_path} not found", file=sys.stderr)
            print("Make sure the tuxedo_io kernel module is loaded.", file=sys.stderr)
            sys.exit(1)
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.dev:
            self.dev.close()

    def _ioctl_read(self, command):
        """Execute an ioctl read command"""
        buf = struct.pack('i', 0)
        result = fcntl.ioctl(self.dev, command, buf)
        return struct.unpack('i', result)[0]

    def _ioctl_write(self, command, value):
        """Execute an ioctl write command"""
        buf = struct.pack('i', value)
        fcntl.ioctl(self.dev, command, buf)

    def get_fan_info(self, fan_num):
        """
        Get fan info for specified fan (0, 1, or 2)
        Returns tuple: (speed_raw, temp1, temp2)
        """
        if fan_num == 0:
            faninfo = self._ioctl_read(R_CL_FANINFO1)
        elif fan_num == 1:
            faninfo = self._ioctl_read(R_CL_FANINFO2)
        elif fan_num == 2:
            faninfo = self._ioctl_read(R_CL_FANINFO3)
        else:
            raise ValueError("fan_num must be 0, 1, or 2")

        # Parse the faninfo value
        # Bits 0-7: Speed (0-255)
        # Bits 8-15: Temp1
        # Bits 16-23: Temp2
        speed_raw = faninfo & 0xff
        temp1 = (faninfo >> 0x08) & 0xff
        temp2 = (faninfo >> 0x10) & 0xff

        # Convert signed if necessary (temperature can be negative in theory)
        if temp1 > 127:
            temp1 = temp1 - 256
        if temp2 > 127:
            temp2 = temp2 - 256

        return (speed_raw, temp1, temp2)

    def get_fan_speed_raw(self, fan_num):
        """Get raw fan speed (0-255)"""
        speed_raw, _, _ = self.get_fan_info(fan_num)
        return speed_raw

    def get_fan_speed_percent(self, fan_num):
        """Get fan speed as percentage (0-100)"""
        speed_raw = self.get_fan_speed_raw(fan_num)
        return round(speed_raw * 100.0 / MAX_FAN_SPEED, 1)

    def get_fan_temperature(self, fan_num):
        """Get temperature for specified fan (uses temp2 which is more reliable)"""
        _, _, temp2 = self.get_fan_info(fan_num)
        return temp2

    def set_fan_speeds(self, fan0_raw, fan1_raw, fan2_raw):
        """
        Set all fan speeds at once (Clevo requires all 3 to be set together)
        Each speed is 0-255 (raw)
        """
        if not all(0 <= s <= MAX_FAN_SPEED for s in [fan0_raw, fan1_raw, fan2_raw]):
            raise ValueError(f"All speeds must be between 0 and {MAX_FAN_SPEED}")

        # Pack into single 32-bit value:
        # Bits 0-7: Fan 0 speed
        # Bits 8-15: Fan 1 speed
        # Bits 16-23: Fan 2 speed
        argument = (fan0_raw & 0xff) | ((fan1_raw & 0xff) << 8) | ((fan2_raw & 0xff) << 16)
        self._ioctl_write(W_CL_FANSPEED, argument)

    def set_fan_speed_percent(self, fan_num, percent):
        """
        Set one fan speed as percentage (0-100)
        Note: Clevo requires setting all 3 fans, so this reads current speeds for others
        """
        if not 0 <= percent <= 100:
            raise ValueError("percent must be between 0 and 100")

        # Read current speeds for all fans
        speeds = [self.get_fan_speed_raw(i) for i in range(3)]

        # Update the specified fan
        speeds[fan_num] = round(MAX_FAN_SPEED * percent / 100.0)

        # Set all fans
        self.set_fan_speeds(speeds[0], speeds[1], speeds[2])

    def set_fans_auto(self):
        """Return all fans to automatic BIOS control"""
        # Set auto bits for all 3 fans
        argument = 0
        argument |= 1        # Enable auto for fan 0
        argument |= 1 << 1   # Enable auto for fan 1
        argument |= 1 << 2   # Enable auto for fan 2
        argument |= 1 << 3   # Enable auto for fan 3 (if present)
        self._ioctl_write(W_CL_FANAUTO, argument)


def cmd_status(args):
    """Show current fan status"""
    with TuxedoFanControlClevo() as fan:
        print("=== Tuxedo Fan Status (Clevo Interface) ===\n")
        print("WARNING: If tccd is running, it may override these values\n")

        for fan_num in range(3):
            try:
                speed_raw, temp1, temp2 = fan.get_fan_info(fan_num)
                speed_percent = round(speed_raw * 100.0 / MAX_FAN_SPEED, 1)

                fan_name = ["CPU", "GPU1", "GPU2"][fan_num]
                print(f"Fan {fan_num} ({fan_name}):")
                print(f"  Speed: {speed_percent}% (raw: {speed_raw}/255)")
                print(f"  Temp1: {temp1}°C")
                print(f"  Temp2: {temp2}°C")

                if temp2 <= 1:
                    print(f"  (Fan {fan_num} may not be present or readable)")
                print()
            except Exception as e:
                print(f"Fan {fan_num}: Error reading ({e})\n")


def cmd_set(args):
    """Set fan speed"""
    with TuxedoFanControlClevo() as fan:
        fan_num = args.fan
        speed = args.speed

        print(f"Setting fan {fan_num} to {speed}%...")
        print("(Note: Clevo interface sets all fans, reading current speeds for others)")
        fan.set_fan_speed_percent(fan_num, speed)
        print("Done!")
        print("\nCurrent status:")

        try:
            speed_raw, temp1, temp2 = fan.get_fan_info(fan_num)
            speed_percent = round(speed_raw * 100.0 / MAX_FAN_SPEED, 1)
            print(f"Fan {fan_num}: {temp2}°C, {speed_percent}%")
        except Exception as e:
            print(f"Error reading back: {e}")


def cmd_auto(args):
    """Return fans to automatic control"""
    with TuxedoFanControlClevo() as fan:
        print("Returning fans to automatic BIOS control...")
        fan.set_fans_auto()
        print("Done!")


def main():
    parser = argparse.ArgumentParser(
        description='Tuxedo Gemini Gen2 Fan Control Utility (Clevo Interface)',
        epilog='WARNING: Stop tccd first to avoid conflicts: sudo systemctl stop tccd'
    )

    subparsers = parser.add_subparsers(dest='command', help='Commands')

    # status command
    parser_status = subparsers.add_parser('status', help='Show current fan status')
    parser_status.set_defaults(func=cmd_status)

    # set command
    parser_set = subparsers.add_parser('set', help='Set fan speed')
    parser_set.add_argument('fan', type=int, choices=[0, 1, 2],
                           help='Fan number (0=CPU, 1=GPU1, 2=GPU2)')
    parser_set.add_argument('speed', type=int,
                           help='Speed percentage (0-100)')
    parser_set.set_defaults(func=cmd_set)

    # auto command
    parser_auto = subparsers.add_parser('auto', help='Return to automatic control')
    parser_auto.set_defaults(func=cmd_auto)

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        sys.exit(1)

    # Check if tccd is running
    if check_tccd_running():
        print("=" * 70)
        print("WARNING: tccd service is currently running!")
        print("=" * 70)
        print("\ntccd has control of the fans and will override any changes you make.")
        print("The values you read may also be incorrect or stale.\n")
        print("To use this utility, you must first stop tccd:")
        print("  sudo systemctl stop tccd\n")
        print("When done, restart tccd:")
        print("  sudo systemctl start tccd\n")
        print("=" * 70)
        response = input("\nContinue anyway? (y/N): ")
        if response.lower() not in ['y', 'yes']:
            print("Aborted.")
            sys.exit(0)
        print()

    args.func(args)


if __name__ == '__main__':
    main()
