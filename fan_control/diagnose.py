#!/usr/bin/env python3
"""
Diagnostic tool to identify which Tuxedo interface is active
"""

import fcntl
import struct
import sys

DEVICE = '/dev/tuxedo_io'

IOCTL_MAGIC = 0xEC
MAGIC_READ_CL = IOCTL_MAGIC + 1   # Clevo
MAGIC_READ_UW = IOCTL_MAGIC + 3   # Uniwill

def _IOR(magic, nr):
    return 0x80000000 | (4 << 16) | (magic << 8) | nr

def _IOW(magic, nr):
    return 0x40000000 | (4 << 16) | (magic << 8) | nr

# Commands to check hardware
R_HWCHECK_CL = _IOR(IOCTL_MAGIC, 0x05)  # Check if Clevo
R_HWCHECK_UW = _IOR(IOCTL_MAGIC, 0x06)  # Check if Uniwill
R_MOD_VERSION = 0x80000000 | (20 << 16) | (IOCTL_MAGIC << 8) | 0x00

# Clevo commands
R_CL_FANINFO1 = _IOR(MAGIC_READ_CL, 0x10)
R_CL_HW_IF_STR = 0x80000000 | (50 << 16) | (MAGIC_READ_CL << 8) | 0x00

# Uniwill commands
R_UW_MODEL_ID = _IOR(MAGIC_READ_UW, 0x01)
R_UW_FAN_TEMP = _IOR(MAGIC_READ_UW, 0x12)
R_UW_HW_IF_STR = 0x80000000 | (50 << 16) | (MAGIC_READ_UW << 8) | 0x00

print("=== Tuxedo Device Diagnostic ===\n")

try:
    with open(DEVICE, 'rb+', buffering=0) as dev:
        print(f"✓ Successfully opened {DEVICE}\n")

        # Check module version
        try:
            buf = bytearray(20)
            result = fcntl.ioctl(dev, R_MOD_VERSION, buf)
            version = buf.decode('utf-8').rstrip('\x00')
            print(f"Module Version: {version}")
        except Exception as e:
            print(f"Module Version: Error ({e})")

        print()

        # Check Clevo interface
        print("Testing Clevo interface...")
        try:
            buf = struct.pack('i', 0)
            result = fcntl.ioctl(dev, R_HWCHECK_CL, buf)
            clevo_check = struct.unpack('i', result)[0]
            if clevo_check == 1:
                print("  ✓ Clevo interface DETECTED")

                # Try to get Clevo interface string
                try:
                    buf = bytearray(50)
                    result = fcntl.ioctl(dev, R_CL_HW_IF_STR, buf)
                    if_str = buf.decode('utf-8').rstrip('\x00')
                    print(f"  Interface: {if_str}")
                except Exception as e:
                    print(f"  Interface string: Error ({e})")

                # Try to read fan info
                try:
                    buf = struct.pack('i', 0)
                    result = fcntl.ioctl(dev, R_CL_FANINFO1, buf)
                    faninfo = struct.unpack('i', result)[0]
                    speed = faninfo & 0xff
                    temp1 = (faninfo >> 0x08) & 0xff
                    temp2 = (faninfo >> 0x10) & 0xff
                    print(f"  Fan 1 info: speed={speed}, temp1={temp1}, temp2={temp2}")
                except Exception as e:
                    print(f"  Fan info: Error ({e})")
            else:
                print("  ✗ Clevo interface not detected")
        except Exception as e:
            print(f"  ✗ Clevo check failed: {e}")

        print()

        # Check Uniwill interface
        print("Testing Uniwill interface...")
        try:
            buf = struct.pack('i', 0)
            result = fcntl.ioctl(dev, R_HWCHECK_UW, buf)
            uniwill_check = struct.unpack('i', result)[0]
            if uniwill_check == 1:
                print("  ✓ Uniwill interface DETECTED")

                # Try to get model ID
                try:
                    buf = struct.pack('i', 0)
                    result = fcntl.ioctl(dev, R_UW_MODEL_ID, buf)
                    model_id = struct.unpack('i', result)[0]
                    print(f"  Model ID: {model_id}")
                except Exception as e:
                    print(f"  Model ID: Error ({e})")

                # Try to read temperature
                try:
                    buf = struct.pack('i', 0)
                    result = fcntl.ioctl(dev, R_UW_FAN_TEMP, buf)
                    temp = struct.unpack('i', result)[0]
                    print(f"  Fan 1 temperature: {temp}°C")
                except Exception as e:
                    print(f"  Fan temperature: Error ({e})")
            else:
                print("  ✗ Uniwill interface not detected")
        except Exception as e:
            print(f"  ✗ Uniwill check failed: {e}")

        print()

except PermissionError:
    print(f"ERROR: Permission denied accessing {DEVICE}")
    print("Run as root: sudo python3 diagnose.py")
    sys.exit(1)
except FileNotFoundError:
    print(f"ERROR: Device {DEVICE} not found")
    print("Make sure tuxedo_io kernel module is loaded")
    sys.exit(1)
except Exception as e:
    print(f"ERROR: {e}")
    sys.exit(1)

print("\n=== Diagnosis Complete ===")
print("\nIf Clevo interface is detected, you need to use Clevo commands.")
print("If Uniwill interface is detected, you need to use Uniwill commands.")
print("If neither is detected, the device may not be supported or module needs updating.")
