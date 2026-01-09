# Tuxedo Gemini Gen2 Fan Control Utilities

Direct fan control for Tuxedo Gemini Gen2 laptops (and other Uniwill-based Tuxedo devices) using the `/dev/tuxedo_io` WMI interface.

## Requirements

- Tuxedo laptop with `tuxedo_io` kernel module loaded
- Python 3.x
- Root privileges

## Installation

```bash
# Make the script executable
chmod +x tuxedo_fan_control.py

# Check if tuxedo_io module is loaded
lsmod | grep tuxedo_io

# Verify device exists
ls -l /dev/tuxedo_io
```

## Usage

### Show Current Fan Status

```bash
sudo ./tuxedo_fan_control.py status
```

Output example:
```
=== Tuxedo Fan Status ===

Hardware minimum speed: 0%
Fans can turn off: Yes

Fan 0 (CPU):
  Temperature: 45°C
  Speed: 35.0%

Fan 1 (GPU):
  Temperature: 42°C
  Speed: 30.0%
```

### Set Fan Speed Manually

```bash
# Set CPU fan (fan 0) to 50%
sudo ./tuxedo_fan_control.py set 0 50

# Set GPU fan (fan 1) to 75%
sudo ./tuxedo_fan_control.py set 1 75
```

### Return to Automatic Control

```bash
sudo ./tuxedo_fan_control.py auto
```

This returns control to the BIOS automatic fan management.

## How It Works

### ioctl() System Calls

Unlike simple character devices that use `read()/write()`, `/dev/tuxedo_io` uses **ioctl()** (input/output control) for sending commands to the kernel driver.

Each ioctl call consists of:
- **Command code**: Tells the driver what operation to perform
- **Data parameter**: Input/output data for the command

Example:
```python
# Read fan temperature
temp = ioctl(device, R_UW_FAN_TEMP, buffer)

# Set fan speed to 50%
ioctl(device, W_UW_FANSPEED, 100)  # 100/200 = 50%
```

### Uniwill Interface Commands

The Gemini Gen2 uses the Uniwill ODM interface with these ioctl commands:

**Read Operations:**
- `R_UW_FAN_TEMP` / `R_UW_FAN_TEMP2` - Read temperature in °C
- `R_UW_FANSPEED` / `R_UW_FANSPEED2` - Read raw speed (0-200)
- `R_UW_FANS_MIN_SPEED` - Get hardware minimum speed
- `R_UW_FANS_OFF_AVAILABLE` - Check if fans can turn off

**Write Operations:**
- `W_UW_FANSPEED` / `W_UW_FANSPEED2` - Set speed (0-200 scale)
- `W_UW_FANAUTO` - Return to automatic BIOS control

### Speed Scale

Uniwill devices use a **0-200 scale** for fan speeds:
- 0 = 0% (fan off)
- 100 = 50%
- 200 = 100%

The utility automatically converts to/from percentages for convenience.

## Why Can't I Use Standard Linux Tools?

Standard tools like `lm-sensors`, `pwmconfig`, and `fancontrol` expect fans to be exposed via the **hwmon** (hardware monitoring) subsystem in sysfs at paths like:

```
/sys/class/hwmon/hwmon*/pwm*        # PWM control
/sys/class/hwmon/hwmon*/fan*_input  # Fan speed readings
```

The Gemini Gen2 **doesn't expose fans via hwmon**. Instead, it uses a proprietary WMI (Windows Management Instrumentation) interface accessible only through `/dev/tuxedo_io` with ioctl commands.

This is why you need device-specific utilities like this one or the full `tccd` daemon.

## Architecture

```
User Space:
  tuxedo_fan_control.py (this utility)
         |
         | ioctl() system calls
         v
Kernel Space:
  /dev/tuxedo_io character device
         |
         v
  tuxedo_io kernel module
         |
         v
  WMI/ACPI firmware interface
         |
         v
Hardware:
  Embedded Controller (EC)
         |
         v
  Physical fans
```

## Safety Notes

- Always use `auto` command to return to automatic control when done
- The BIOS/EC has built-in thermal protection
- Setting fans too low may cause thermal throttling
- The system will override dangerously low fan speeds

## References

- `/opt/tcc2/src/native-lib/tuxedo_io_lib/tuxedo_io_ioctl.h` - ioctl command definitions
- `/opt/tcc2/src/native-lib/tuxedo_io_lib/tuxedo_io_api.hh` - C++ API reference
- `/dev/tuxedo_io` - Kernel device interface

## License

GPLv3 - Same as tuxedo-control-center

## Author

Created for Tuxedo Gemini Gen2 fan control investigation
