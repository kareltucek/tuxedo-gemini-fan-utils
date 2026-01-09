#!/usr/bin/env python3
"""
Tuxedo Gemini Gen2 Fan Control Utility

Direct fan control for Tuxedo laptops using the /dev/tuxedo_io WMI interface.
Supports Uniwill-based devices (like Gemini Gen2).

Requires root privileges to access /dev/tuxedo_io
"""

import fcntl
import struct
import sys
import argparse

# Device file
DEVICE = '/dev/tuxedo_io'

# ioctl magic numbers
IOCTL_MAGIC = 0xEC
MAGIC_READ_UW = IOCTL_MAGIC + 3
MAGIC_WRITE_UW = IOCTL_MAGIC + 4

# Helper functions to create ioctl command numbers
def _IOR(magic, nr):
    """Create ioctl read command number"""
    return 0x80000000 | (4 << 16) | (magic << 8) | nr

def _IOW(magic, nr):
    """Create ioctl write command number"""
    return 0x40000000 | (4 << 16) | (magic << 8) | nr

def _IO(magic, nr):
    """Create ioctl command number (no data)"""
    return (magic << 8) | nr

# Uniwill interface ioctl commands
R_UW_FAN_TEMP = _IOR(MAGIC_READ_UW, 0x12)   # Read fan 1 temperature
R_UW_FAN_TEMP2 = _IOR(MAGIC_READ_UW, 0x13)  # Read fan 2 temperature
R_UW_FANSPEED = _IOR(MAGIC_READ_UW, 0x10)   # Read fan 1 speed
R_UW_FANSPEED2 = _IOR(MAGIC_READ_UW, 0x11)  # Read fan 2 speed
R_UW_FANS_MIN_SPEED = _IOR(MAGIC_READ_UW, 0x17)  # Get hardware minimum speed
R_UW_FANS_OFF_AVAILABLE = _IOR(MAGIC_READ_UW, 0x16)  # Check if fans can turn off

W_UW_FANSPEED = _IOW(MAGIC_WRITE_UW, 0x10)  # Set fan 1 speed
W_UW_FANSPEED2 = _IOW(MAGIC_WRITE_UW, 0x11) # Set fan 2 speed
W_UW_FANAUTO = _IO(MAGIC_WRITE_UW, 0x14)    # Return to automatic control

# Max fan speed for Uniwill devices (200 = 100%)
MAX_FAN_SPEED = 200


class TuxedoFanControl:
    """Interface to Tuxedo fan control via /dev/tuxedo_io"""

    def __init__(self, device_path=DEVICE):
        self.device_path = device_path
        self.dev = None

    def __enter__(self):
        try:
            self.dev = open(self.device_path, 'rb+', buffering=0)
        except PermissionError:
            print(f"ERROR: Permission denied accessing {self.device_path}", file=sys.stderr)
            print("This utility requires root privileges. Try: sudo python3 tuxedo_fan_control.py", file=sys.stderr)
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

    def _ioctl_call(self, command):
        """Execute an ioctl command with no data"""
        fcntl.ioctl(self.dev, command, 0)

    def get_fan_temperature(self, fan_num):
        """Get temperature for specified fan (0 or 1)"""
        if fan_num == 0:
            return self._ioctl_read(R_UW_FAN_TEMP)
        elif fan_num == 1:
            return self._ioctl_read(R_UW_FAN_TEMP2)
        else:
            raise ValueError("fan_num must be 0 or 1")

    def get_fan_speed_raw(self, fan_num):
        """Get raw fan speed for specified fan (0-200 scale)"""
        if fan_num == 0:
            return self._ioctl_read(R_UW_FANSPEED)
        elif fan_num == 1:
            return self._ioctl_read(R_UW_FANSPEED2)
        else:
            raise ValueError("fan_num must be 0 or 1")

    def get_fan_speed_percent(self, fan_num):
        """Get fan speed as percentage (0-100)"""
        raw_speed = self.get_fan_speed_raw(fan_num)
        return round(raw_speed * 100.0 / MAX_FAN_SPEED, 1)

    def set_fan_speed_raw(self, fan_num, speed):
        """Set fan speed (0-200 scale)"""
        if not 0 <= speed <= MAX_FAN_SPEED:
            raise ValueError(f"speed must be between 0 and {MAX_FAN_SPEED}")

        if fan_num == 0:
            self._ioctl_write(W_UW_FANSPEED, speed)
        elif fan_num == 1:
            self._ioctl_write(W_UW_FANSPEED2, speed)
        else:
            raise ValueError("fan_num must be 0 or 1")

    def set_fan_speed_percent(self, fan_num, percent):
        """Set fan speed as percentage (0-100)"""
        if not 0 <= percent <= 100:
            raise ValueError("percent must be between 0 and 100")

        raw_speed = round(MAX_FAN_SPEED * percent / 100.0)
        self.set_fan_speed_raw(fan_num, raw_speed)

    def set_fans_auto(self):
        """Return both fans to automatic BIOS control"""
        self._ioctl_call(W_UW_FANAUTO)

    def get_fans_min_speed(self):
        """Get hardware minimum fan speed"""
        return self._ioctl_read(R_UW_FANS_MIN_SPEED)

    def get_fans_off_available(self):
        """Check if fans can be completely turned off"""
        result = self._ioctl_read(R_UW_FANS_OFF_AVAILABLE)
        return result == 1


def cmd_status(args):
    """Show current fan status"""
    with TuxedoFanControl() as fan:
        print("=== Tuxedo Fan Status ===\n")

        # Hardware capabilities
        min_speed = fan.get_fans_min_speed()
        fans_off = fan.get_fans_off_available()
        print(f"Hardware minimum speed: {min_speed}%")
        print(f"Fans can turn off: {'Yes' if fans_off else 'No'}\n")

        # Fan 0 (CPU)
        try:
            temp0 = fan.get_fan_temperature(0)
            speed0 = fan.get_fan_speed_percent(0)
            print(f"Fan 0 (CPU):")
            print(f"  Temperature: {temp0}°C")
            print(f"  Speed: {speed0}%")
        except Exception as e:
            print(f"Fan 0 (CPU): Error reading ({e})")

        # Fan 1 (GPU)
        try:
            temp1 = fan.get_fan_temperature(1)
            speed1 = fan.get_fan_speed_percent(1)
            print(f"\nFan 1 (GPU):")
            print(f"  Temperature: {temp1}°C")
            print(f"  Speed: {speed1}%")
        except Exception as e:
            print(f"\nFan 1 (GPU): Error reading ({e})")


def cmd_set(args):
    """Set fan speed"""
    with TuxedoFanControl() as fan:
        fan_num = args.fan
        speed = args.speed

        print(f"Setting fan {fan_num} to {speed}%...")
        fan.set_fan_speed_percent(fan_num, speed)
        print("Done!")
        print("\nCurrent status:")

        temp = fan.get_fan_temperature(fan_num)
        actual_speed = fan.get_fan_speed_percent(fan_num)
        print(f"Fan {fan_num}: {temp}°C, {actual_speed}%")


def cmd_auto(args):
    """Return fans to automatic control"""
    with TuxedoFanControl() as fan:
        print("Returning fans to automatic BIOS control...")
        fan.set_fans_auto()
        print("Done!")


def main():
    parser = argparse.ArgumentParser(
        description='Tuxedo Gemini Gen2 Fan Control Utility',
        epilog='Requires root privileges. Example: sudo python3 tuxedo_fan_control.py status'
    )

    subparsers = parser.add_subparsers(dest='command', help='Commands')

    # status command
    parser_status = subparsers.add_parser('status', help='Show current fan status')
    parser_status.set_defaults(func=cmd_status)

    # set command
    parser_set = subparsers.add_parser('set', help='Set fan speed')
    parser_set.add_argument('fan', type=int, choices=[0, 1],
                           help='Fan number (0=CPU, 1=GPU)')
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

    args.func(args)


if __name__ == '__main__':
    main()
