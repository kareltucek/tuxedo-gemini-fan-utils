# Tuxedo Gemini Gen2 Fan Control

Simple fan control utility for Tuxedo Gemini Gen2 laptops using the Clevo interface via `/dev/tuxedo_io`.

## Requirements

- Tuxedo laptop with `tuxedo_io` kernel module loaded
- GCC compiler
- Root privileges

## Installation

```bash
# Build the utility
make

# Check that tuxedo_io module is loaded
lsmod | grep tuxedo_io

# Verify device exists
ls -l /dev/tuxedo_io
```

## Usage

### Show Current Fan Status

```bash
sudo ./fanctl status
```

Output example:
```
=== Tuxedo Fan Status ===

Fan 0 (CPU):
  Speed: 35.3% (raw: 90/255)
  Temp1: 52°C
  Temp2: 66°C

Fan 1 (GPU):
  Speed: 35.3% (raw: 90/255)
  Temp1: 56°C
  Temp2: 57°C
```

### Set Fan Speed Manually

```bash
# Set CPU fan (fan 0) to 50%
sudo ./fanctl set 0 50

# Set GPU fan (fan 1) to 75%
sudo ./fanctl set 1 75
```

**Fan numbers:**
- `0` = CPU fan
- `1` = GPU fan

**Note:** The Clevo interface requires setting all fans together, so the utility reads current speeds for other fans before making changes.

### Return to Automatic Control

```bash
sudo ./fanctl auto
```

This returns control to the BIOS automatic fan management.

## How It Works

### Clevo Interface via ioctl()

The Gemini Gen2 uses the **Clevo interface** (not Uniwill) which is accessed through ioctl system calls to `/dev/tuxedo_io`.

**Key ioctl commands:**

- `R_CL_FANINFO1` (0xED01 + 0x10) - Read fan 1 info
- `R_CL_FANINFO2` (0xED01 + 0x11) - Read fan 2 info
- `W_CL_FANSPEED` (0xED02 + 0x10) - Set all fan speeds
- `W_CL_FANAUTO` (0xED02 + 0x11) - Return to auto mode

### Fan Info Format

Each `FANINFO` ioctl returns a 32-bit value:
- **Bits 0-7**: Fan speed (0-255)
- **Bits 8-15**: Temperature sensor 1 (°C)
- **Bits 16-23**: Temperature sensor 2 (°C)

Temperature sensor 2 is generally more reliable.

### Setting Fan Speeds

The `W_CL_FANSPEED` ioctl requires all fan speeds in one call:
- **Bits 0-7**: Fan 0 speed (0-255)
- **Bits 8-15**: Fan 1 speed (0-255)
- **Bits 16-23**: Fan 2 speed (0-255)

This is why changing one fan requires reading the others first.

## Why Not Python?

Initial Python implementations using `fcntl.ioctl()` returned zeros or didn't work reliably. The C implementation using `sys/ioctl.h` works correctly with the kernel driver.

## Architecture

```
User Space:
  fanctl (this utility)
         |
         | ioctl() system calls
         v
Kernel Space:
  /dev/tuxedo_io character device
         |
         v
  tuxedo_io kernel module (clevo_acpi interface)
         |
         v
  ACPI/WMI firmware interface
         |
         v
Hardware:
  Embedded Controller (EC)
         |
         v
  Physical fans
```

## Safety Notes

- The BIOS/EC has built-in thermal protection
- Setting fans too low may cause thermal throttling
- Always return to auto mode when done: `sudo ./fanctl auto`
- The system will override dangerously low fan speeds

## Files

- `fanctl.c` - Main fan control utility
- `Makefile` - Build configuration

## Building

```bash
# Build
make

# Clean compiled files
make clean
```

## Troubleshooting

### "Failed to open /dev/tuxedo_io"
- Make sure you're running as root (`sudo`)
- Check if tuxedo_io module is loaded: `lsmod | grep tuxedo_io`
- Load module if needed: `sudo modprobe tuxedo_io`

### Fans not responding
- Make sure tccd is not running: `sudo systemctl stop tccd`
- tccd will compete for control of the fans
- Restart tccd when done: `sudo systemctl start tccd`

### Reading zeros or no change
- The EC may be in auto mode
- Some operations require specific initialization
- Try `sudo ./fanctl auto` then set speeds again

## References

- `/usr/src/tuxedo-drivers-*/tuxedo_io/tuxedo_io_ioctl.h` - ioctl definitions
- `/opt/tcc2/src/native-lib/tuxedo_io_lib/` - TCC implementation
- Tuxedo Drivers: https://github.com/tuxedocomputers/tuxedo-drivers

## License

GPLv3 - Same as tuxedo-control-center

## Author

Created for Tuxedo Gemini Gen2 fan control
