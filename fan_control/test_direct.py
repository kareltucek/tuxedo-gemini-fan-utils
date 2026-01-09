#!/usr/bin/env python3
"""
Test direct fan control without hardware check
"""

import fcntl
import struct
import sys

DEVICE = '/dev/tuxedo_io'

IOCTL_MAGIC = 0xEC
MAGIC_READ_UW = IOCTL_MAGIC + 3
MAGIC_WRITE_UW = IOCTL_MAGIC + 4

def _IOR(magic, nr):
    return 0x80000000 | (4 << 16) | (magic << 8) | nr

def _IOW(magic, nr):
    return 0x40000000 | (4 << 16) | (magic << 8) | nr

def _IO(magic, nr):
    return (magic << 8) | nr

# Uniwill commands
R_UW_FAN_TEMP = _IOR(MAGIC_READ_UW, 0x12)
R_UW_FANSPEED = _IOR(MAGIC_READ_UW, 0x10)
W_UW_FANSPEED = _IOW(MAGIC_WRITE_UW, 0x10)
W_UW_FANAUTO = _IO(MAGIC_WRITE_UW, 0x14)

# Clevo commands
MAGIC_READ_CL = IOCTL_MAGIC + 1
MAGIC_WRITE_CL = IOCTL_MAGIC + 2

R_CL_FANINFO1 = _IOR(MAGIC_READ_CL, 0x10)
W_CL_FANSPEED = _IOW(MAGIC_WRITE_CL, 0x10)
W_CL_FANAUTO = _IOW(MAGIC_WRITE_CL, 0x11)

print("=== Testing Direct Fan Control ===\n")

try:
    with open(DEVICE, 'rb+', buffering=0) as dev:
        print("Testing Uniwill commands...")

        # Try to read temperature
        try:
            buf = struct.pack('i', 0)
            result = fcntl.ioctl(dev, R_UW_FAN_TEMP, buf)
            temp = struct.unpack('i', result)[0]
            print(f"  ✓ R_UW_FAN_TEMP: {temp}°C")
            if temp > 0:
                print("  → Uniwill interface is working!")
        except Exception as e:
            print(f"  ✗ R_UW_FAN_TEMP failed: {e}")

        # Try to read fan speed
        try:
            buf = struct.pack('i', 0)
            result = fcntl.ioctl(dev, R_UW_FANSPEED, buf)
            speed = struct.unpack('i', result)[0]
            print(f"  ✓ R_UW_FANSPEED: {speed} (raw)")
            if speed > 0:
                print("  → Uniwill fan reading works!")
        except Exception as e:
            print(f"  ✗ R_UW_FANSPEED failed: {e}")

        print("\nTesting Clevo commands...")

        # Try to read Clevo fan info
        try:
            buf = struct.pack('i', 0)
            result = fcntl.ioctl(dev, R_CL_FANINFO1, buf)
            faninfo = struct.unpack('i', result)[0]
            speed = faninfo & 0xff
            temp1 = (faninfo >> 0x08) & 0xff
            temp2 = (faninfo >> 0x10) & 0xff
            print(f"  ✓ R_CL_FANINFO1: speed={speed}, temp1={temp1}°C, temp2={temp2}°C")
            if temp2 > 0:
                print("  → Clevo interface is working!")
        except Exception as e:
            print(f"  ✗ R_CL_FANINFO1 failed: {e}")

        print("\n=== Results ===")
        print("If any command returned valid data (temp > 0), that interface works.")
        print("The HWCHECK might be broken but the actual fan controls could still work.")

except PermissionError:
    print(f"ERROR: Permission denied. Run as root: sudo python3 test_direct.py")
    sys.exit(1)
except Exception as e:
    print(f"ERROR: {e}")
    sys.exit(1)
