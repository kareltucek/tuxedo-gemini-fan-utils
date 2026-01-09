# PID Fan Controller

Automatic temperature-based fan controller using PID algorithm for Tuxedo Gemini Gen2.

## Overview

This script maintains a target CPU temperature by automatically adjusting fan speeds using a PID (Proportional-Integral-Derivative) control algorithm. It runs continuously at 1 Hz and sets both CPU and GPU fans to the same speed.

## Requirements

- Working `fanctl` binary in `../fan_control/fanctl`
- Python 3.x
- Root privileges

## Usage

```bash
sudo ./fan-pid-control.py [-t] <min_speed> <max_speed> <target_temp>
```

### Arguments

- `-t` - **Test mode**: Calculate and display fan speeds without actually setting them
- `min_speed` - Minimum fan speed percentage (0-100)
- `max_speed` - Maximum fan speed percentage (0-100)
- `target_temp` - Target CPU temperature in Celsius (20-95)

### Examples

```bash
# Test mode - see what it would do without actually controlling fans
sudo ./fan-pid-control.py -t 30 100 70

# Live mode - actually control fans to maintain 70°C
sudo ./fan-pid-control.py 30 100 70

# Quiet office work (higher temp, lower max fan speed)
sudo ./fan-pid-control.py 20 60 75

# Gaming (aggressive cooling)
sudo ./fan-pid-control.py 40 100 65

# Balanced (default recommendation)
sudo ./fan-pid-control.py 30 100 70
```

## Output Format

```
[TEST] [   1] Temp:  62.0°C | Target: 70.0°C | Error:  -8.0°C | Fan:  30.0% | P:-24.00 I: -0.17 D: +0.00
[LIVE] [   2] Temp:  63.0°C | Target: 70.0°C | Error:  -7.0°C | Fan:  30.0% | P:-21.00 I: -0.35 D: +1.00
```

### Fields

- **[TEST]/[LIVE]** - Operating mode
- **Iteration number** - Counter
- **Temp** - Current CPU temperature (from temp2 sensor)
- **Target** - Desired temperature
- **Error** - Current minus target (positive = too hot, negative = too cold)
- **Fan** - Commanded fan speed percentage (this is the output)
- **P** - Proportional term contribution
- **I** - Integral term contribution
- **D** - Derivative term contribution

## PID Algorithm

The controller uses three terms to calculate fan speed:

### P (Proportional) Term
- **Kp = 3.0**
- Responds immediately to current temperature error
- Example: If 5°C too hot, adds 15% fan speed (3.0 × 5)

### I (Integral) Term
- **Ki = 0.2**
- Eliminates steady-state error over time
- Accumulates error to ensure target is reached
- Has anti-windup protection to prevent overshooting

### D (Derivative) Term
- **Kd = 1.0**
- Dampens oscillations by predicting future error
- Looks at rate of temperature change
- Skipped on first iteration to avoid garbage values

### Formula

```
output = (Kp × error) + (Ki × ∫error dt) + (Kd × d(error)/dt)
```

Then clamped to [min_speed, max_speed] range.

## How It Works

1. **Read temperature** from CPU fan sensor using `fanctl status`
2. **Calculate error** = current_temp - target_temp
3. **Apply PID algorithm** to compute desired fan speed
4. **Clamp to limits** (min_speed to max_speed)
5. **Set both fans** to calculated speed using `fanctl set`
6. **Wait 1 second** and repeat

## Tuning

If the default PID parameters don't work well for your use case, edit the script:

```python
kp = 3.0   # Proportional gain
ki = 0.2   # Integral gain
kd = 1.0   # Derivative gain
```

### Tuning Guidelines

**Temperature oscillates:**
- Decrease Kp (less aggressive)
- Increase Kd (more damping)

**Too slow to respond:**
- Increase Kp (more aggressive)
- Increase Ki (faster correction)

**Overshoots target:**
- Increase Kd (more damping)
- Decrease Kp (less aggressive)

**Steady-state offset:**
- Increase Ki (stronger long-term correction)

## Stopping

Press **Ctrl+C** to stop. The script will:
- In live mode: Return fans to automatic BIOS control
- In test mode: Just exit cleanly

## Safety

- Temperature reading every second prevents runaway
- Min/max limits enforced on fan speed
- Anti-windup protection prevents integral term overflow
- Fans return to auto mode on exit
- Uses proven `fanctl` binary for hardware control

## Test Mode

Use `-t` flag to see what the controller would do without actually setting fan speeds. Perfect for:
- Testing PID parameters
- Understanding controller behavior
- Verifying temperature readings
- Checking if fans would oscillate

## Integration

### Systemd Service

Create `/etc/systemd/system/fan-pid.service`:

```ini
[Unit]
Description=PID Fan Controller
After=multi-user.target

[Service]
Type=simple
ExecStart=/opt/tuxedo-gemini-fan-utils/pid_control/fan-pid-control.py 30 100 70
Restart=on-failure

[Install]
WantedBy=multi-user.target
```

Enable and start:
```bash
sudo systemctl daemon-reload
sudo systemctl enable fan-pid.service
sudo systemctl start fan-pid.service
```

## Troubleshooting

### "fanctl not found"
```bash
cd ../fan_control
make
```

### "Permission denied"
Run with `sudo`

### Fans not responding
- Stop tccd: `sudo systemctl stop tccd`
- tccd competes for fan control

### Reading errors
Check if device is accessible:
```bash
ls -l /dev/tuxedo_io
lsmod | grep tuxedo_io
```

## Code Structure

The PID controller is organized into multiple modules:

```
pid_control/
├── __init__.py              - Package initialization
├── fan-pid-control.py       - Main script (entry point)
├── pid_controller.py        - PID algorithm implementation
├── fan_controller.py        - Hardware interface (fanctl wrapper)
├── config.py                - Configuration and validation
└── README.md                - This file
```

### Modules

**fan-pid-control.py**
- Main entry point
- Argument parsing
- Control loop
- Signal handling

**pid_controller.py**
- `PIDController` class
- PID algorithm with P, I, D terms
- Anti-windup protection
- Output clamping

**fan_controller.py**
- `FanController` class
- Interfaces with `fanctl` binary
- Parses fan status output
- Sends fan speed commands

**config.py**
- `PIDConfig` class - PID tuning parameters
- `ValidationConfig` class - Input validation limits
- `validate_arguments()` function

## Architecture

```
fan-pid-control.py
    |
    | imports
    v
pid_controller.py, fan_controller.py, config.py
    |
    | subprocess calls
    v
fanctl binary
    |
    | ioctl() system calls
    v
/dev/tuxedo_io (Clevo interface)
    |
    v
Embedded Controller
    |
    v
Physical fans
```

## License

GPLv3 - Same as tuxedo-control-center
