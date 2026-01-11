# PID Fan Controller

Automatic temperature-based fan controller using PID algorithm for Tuxedo Gemini Gen2.

## Overview

This script maintains a target CPU temperature by automatically adjusting fan speeds using a PID (Proportional-Integral-Derivative) control algorithm. It runs continuously at 2 Hz (0.5s intervals, configurable) and sets both CPU and GPU fans to the same speed.

**Key features:**
- Dual temperature sources (fast coretemp + slow fanctl sensors) for optimal response
- Multi-level exponential smoothing to prevent oscillations
- Conditional integration anti-windup
- One-sided integral (cooling only)
- Real-time status display with PID terms in both physical and percentage units

## Requirements

- Working `fanctl` binary in `../fan_control/fanctl`
- Python 3.x
- Root privileges

## Usage

```bash
sudo ./fan-pid-control.py [-t] [-i interval] [min_speed max_speed target_temp]
```

### Arguments

- `-t` - **Test mode**: Calculate and display fan speeds without actually setting them
- `-i interval` - **Update interval** in seconds (0.1-10.0, default: from ControlConfig.UPDATE_INTERVAL)
- `min_speed` - Minimum fan speed percentage (0-100, default: from ControlConfig.MIN_SPEED)
- `max_speed` - Maximum fan speed percentage (0-100, default: from ControlConfig.MAX_SPEED)
- `target_temp` - Target CPU temperature in Celsius (20-95, default: from ControlConfig.TARGET_TEMP)

All three control parameters are optional. If omitted, defaults from `config.py` are used.

### Examples

```bash
# Use defaults from config.py (10-30% range, 65°C target, 0.5s interval)
sudo ./fan-pid-control.py

# Test mode - see what it would do without actually controlling fans
sudo ./fan-pid-control.py -t

# Test mode with custom parameters
sudo ./fan-pid-control.py -t 30 100 70

# Live mode - actually control fans to maintain 70°C
sudo ./fan-pid-control.py 30 100 70

# Quiet office work (higher temp, lower max fan speed)
sudo ./fan-pid-control.py 20 60 75

# Gaming (aggressive cooling)
sudo ./fan-pid-control.py 40 100 65

# Fast updates (5 Hz = 0.2s interval)
sudo ./fan-pid-control.py -i 0.2 30 100 70

# Slow updates (1 Hz = 1.0s interval)
sudo ./fan-pid-control.py -i 1.0 30 100 70
```

## Output Format

```
[TEST] 66.0°C (pkg: 65.5 fan: 66.5) | Tgt: 65.0°C | Err: +1.0°C | Fan: 22.5% | PID +1.0 +0.5 +0.2 °C | PID: +3.0 +0.1 +2.0 %fanspeed
67.0°C (pkg: 67.0 fan: 67.0) | Tgt: 65.0°C | Err: +2.0°C | Fan: 24.8% | PID +2.0 +1.2 +0.5 °C | PID: +6.0 +0.2 +5.0 %fanspeed
65.0°C (pkg: 64.5 fan: 65.5) | Tgt: 65.0°C | Err: +0.0°C | Fan: 20.0% | PID +0.0 +0.8 -0.3 °C | PID: +0.0 +0.2 -3.0 %fanspeed
```

### Fields

- **[TEST]** - Shows "[TEST] " prefix only in test mode, no prefix in live mode
- **Temp** - Combined temperature (average of cpu_package and max fanctl sensor)
- **(pkg: X fan: Y)** - Individual temperature sources: coretemp CPU package and fanctl max sensor
- **Tgt** - Desired temperature
- **Err** - Current minus target (positive = too hot, negative = too cold)
- **Fan** - Commanded fan speed percentage (base_speed + P + I + D, clamped to min/max)
- **PID ... °C** - P, I, D terms as temperature-equivalent contributions (how many degrees of error would produce this contribution)
  - P term: actual temperature error
  - I term: integral contribution expressed as equivalent temperature error (i_term / Kp)
  - D term: derivative contribution expressed as rate of change
- **PID: ... %fanspeed** - P, I, D terms as fan speed percentage contributions

## PID Algorithm

The controller uses a PID algorithm with three terms operating around a base speed (midpoint of fan range):

### P (Proportional) Term
- **Kp = 3.0**
- Responds immediately to current temperature error
- Example: If 5°C too hot, adds 15% fan speed (3.0 × 5)

### I (Integral) Term
- **Ki = 0.2**
- Eliminates steady-state error by accumulating error over time
- One-sided: only accumulates when temp > target (cooling control only)
- Dynamic limits: can only fill remaining headroom after P+D contributions, with minimum quarter-range guarantee
- Conditional integration anti-windup: stops accumulating when previous output was saturated
- Example: If error persists for 10 seconds, adds 2% fan speed (0.2 × 10)

### D (Derivative) Term
- **Kd = 10.0**
- Responds to rate of temperature change for immediate reaction
- Calculates d(error)/dt = d(temp - target)/dt = d(temp)/dt (since target is constant)
- Exponentially smoothed to reduce oscillations (configurable half-life, default 1s)
- Smoothing includes compensation scaling (multiply by 2/halflife) to maintain proper gain
- Example: If temp rising at 2°C/s, adds 20% fan speed (10.0 × 2)

### Formula

```
base_speed = (min_speed + max_speed) / 2
output = base_speed + (Kp × error) + (Ki × ∫error dt) + (Kd × d(error)/dt)
```

Then clamped to [min_speed, max_speed] range.

**Key insight**: The controller operates around the midpoint of the fan range. At target temperature with no error, the fan runs at base_speed (e.g., 20% for a 10-30% range), not at minimum speed.

## How It Works

1. **Read temperatures** from two sources:
   - **coretemp**: CPU package temperature (fast updates, 10-100 Hz, smoothed with 1s half-life)
   - **fanctl**: Max temperature across fan sensors (slow updates, 1-2 Hz, smoothed with 2s half-life)
   - **Combined**: Average of both sources for optimal balance
2. **Calculate error** = current_temp - target_temp
3. **Apply PID algorithm** to compute desired fan speed around base_speed
4. **Smooth D term** (exponentially, 1s half-life) to reduce oscillations
5. **Smooth final output** (exponentially, 4s half-life) to prevent wild fan speed changes
6. **Clamp to limits** (min_speed to max_speed)
7. **Set both fans** to calculated speed using `fanctl set`
8. **Wait** (default 0.5s) and repeat

The multi-level smoothing prevents oscillations while maintaining good responsiveness to actual temperature changes.

## Tuning

If the default parameters don't work well for your use case, edit `config.py`:

```python
class PIDConfig:
    KP = 3.0    # Proportional gain
    KI = 0.2    # Integral gain
    KD = 10.0   # Derivative gain
    ONE_SIDED_INTEGRAL = True  # One-sided (cooling only) vs bidirectional

class ControlConfig:
    MIN_SPEED = 10         # Minimum fan speed %
    MAX_SPEED = 30         # Maximum fan speed %
    TARGET_TEMP = 65       # Target temperature °C
    UPDATE_INTERVAL = 0.5  # Update interval in seconds

class SmoothingConfig:
    CORETEMP_HALFLIFE = 1.0    # CPU package temp smoothing
    FANCTL_TEMP_HALFLIFE = 2.0  # Fanctl sensor smoothing
    D_TERM_HALFLIFE = 1.0       # Derivative term smoothing
    FANSPEED_HALFLIFE = 4.0     # Final fan speed smoothing
```

### Tuning Guidelines

**Temperature oscillates:**
- Decrease Kp (less aggressive response to error)
- Decrease Kd (less aggressive response to rate changes)
- Increase FANSPEED_HALFLIFE or D_TERM_HALFLIFE (more smoothing)

**Too slow to respond:**
- Increase Kp (more aggressive)
- Increase Kd (faster response to temperature changes)
- Decrease smoothing half-lives (less smoothing, faster response)

**Overshoots target:**
- Decrease Kd (less aggressive on rate changes)
- Decrease Kp (less aggressive on error)
- Increase FANSPEED_HALFLIFE (slower fan speed changes)

**Steady-state offset (temp settles away from target):**
- Increase Ki (faster integral accumulation)
- Set ONE_SIDED_INTEGRAL = False for bidirectional integral (provides averaging)

**Fans too noisy/aggressive:**
- Reduce Kd (main contributor to rapid fan speed changes)
- Increase FANSPEED_HALFLIFE (slower fan speed transitions)
- Increase update interval with `-i` flag (e.g., `-i 1.0` for slower updates)
- Narrow the fan speed range (e.g., 15-25% instead of 10-30%)

### Debug Mode

For debugging purposes, you can disable smoothing by setting half-life values to 0:
- **D_TERM_HALFLIFE = 0** - Disables D term smoothing (uses raw derivative)
- **FANSPEED_HALFLIFE = 0** - Disables fan speed smoothing (immediate response)

This allows you to observe the raw controller behavior without smoothing effects.

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
├── coretemp_reader.py       - CPU package temperature reader
├── fanctl_temp_reader.py    - Fanctl temperature sensor reader
├── config.py                - Configuration and validation
└── README.md                - This file
```

### Modules

**fan-pid-control.py**
- Main entry point
- Argument parsing
- Control loop with dual temperature sources
- Signal handling

**pid_controller.py**
- `PIDController` class
- PID algorithm with P, I, D terms
- Conditional integration anti-windup
- Exponential smoothing for D term and final output
- Output clamping around base speed (midpoint of range)

**fan_controller.py**
- `FanController` class
- Interfaces with `fanctl` binary
- Parses fan status output
- Sends fan speed commands

**coretemp_reader.py**
- `CoretempReader` class
- Reads CPU package temperature from hwmon
- Exponential smoothing (configurable half-life)
- Fast updates (10-100 Hz)

**fanctl_temp_reader.py**
- `FanctlTempReader` class
- Reads temperatures from fanctl sensors
- Returns smoothed maximum across all sensors
- Slow updates (1-2 Hz)

**config.py**
- `PIDConfig` class - PID tuning parameters (Kp, Ki, Kd, ONE_SIDED_INTEGRAL)
- `ControlConfig` class - Default control parameters (speeds, target, interval)
- `SmoothingConfig` class - Exponential smoothing half-lives
- `ValidationConfig` class - Input validation limits
- `validate_arguments()` function

## Architecture

```
fan-pid-control.py
    |
    | imports
    v
pid_controller.py, fan_controller.py, coretemp_reader.py, fanctl_temp_reader.py, config.py
    |
    +-- coretemp_reader.py -----> /sys/class/hwmon/hwmon*/temp*_input (CPU package temp)
    |
    +-- fanctl_temp_reader.py --> fanctl binary --> /dev/tuxedo_io (fan sensor temps)
    |
    +-- fan_controller.py -------> fanctl binary --> /dev/tuxedo_io (fan control)
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
