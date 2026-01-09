# Tuxedo Gemini Gen2 Fan Control Utilities

Fan control utilities for Tuxedo Gemini Gen2 laptops.

## Tools

### 1. fanctl - Manual Fan Control

Located in `fan_control/fanctl.c` - Simple utility for manual fan control.

```bash
cd fan_control
make
sudo ./fanctl status      # Show fan status
sudo ./fanctl set 0 50    # Set CPU fan to 50%
sudo ./fanctl auto        # Return to automatic control
```

See `fan_control/README.md` for detailed documentation.

### 2. fan-pid-control.py - PID Temperature Controller

Automatic fan controller that maintains a target temperature using a PID algorithm.

```bash
# Usage: sudo ./pid_control/fan-pid-control.py <min_speed%> <max_speed%> <target_temp°C>

# Example: Maintain 70°C with fan speeds between 30-100%
sudo ./pid_control/fan-pid-control.py 30 100 70
```

**Features:**
- Runs continuously (1 Hz update rate)
- PID controller automatically adjusts fan speeds
- Sets both CPU and GPU fans to same speed
- Graceful shutdown on Ctrl+C (returns to auto mode)
- Real-time status display with PID terms

**Example output:**
```
======================================================================
PID Fan Controller
======================================================================
Target temperature: 70°C
Fan speed range: 30% - 100%
PID parameters: Kp=3.0, Ki=0.2, Kd=1.0

Press Ctrl+C to stop and return to automatic control
======================================================================

[   1] Temp:  66.0°C | Target: 70.0°C | Error: -4.0°C | Fan:  30.0% | P:-12.00 I: -0.80 D: -4.00
[   2] Temp:  65.0°C | Target: 70.0°C | Error: -5.0°C | Fan:  30.0% | P:-15.00 I: -1.80 D: -1.00
[   3] Temp:  67.0°C | Target: 70.0°C | Error: -3.0°C | Fan:  30.0% | P: -9.00 I: -2.40 D: +2.00
```

**PID Parameters:**
- **Kp (Proportional)**: 3.0 - Increase fan 3% per degree above target
- **Ki (Integral)**: 0.2 - Eliminate steady-state error
- **Kd (Derivative)**: 1.0 - Dampen oscillations

These can be adjusted in the script if needed.

**How PID works:**
- **P term**: Reacts to current error (temp - target)
- **I term**: Eliminates persistent offset
- **D term**: Reduces overshoot and oscillation

**Safety:**
- Enforces min/max fan speed limits
- Returns to auto mode on exit
- Anti-windup protection for integral term
- Temperature-based control only (no time-based ramping)

## Requirements

- Tuxedo laptop with `tuxedo_io` kernel module
- Python 3.x (for PID controller)
- GCC (for fanctl)
- Root privileges

## Installation

```bash
# Clone or download this repository
cd /opt/tuxedo-gemini-fan-utils

# Build fanctl
cd fan_control
make

# Test fanctl
sudo ./fanctl status

# Test PID controller
cd ..
sudo ./fan-pid-control.py 30 100 70
```

## Usage Scenarios

### Scenario 1: Manual Control
Use `fanctl` when you want direct control:
```bash
sudo ./fan_control/fanctl set 0 60   # Set CPU fan to 60%
# Do your work
sudo ./fan_control/fanctl auto       # Return to auto
```

### Scenario 2: Temperature Target
Use `pid_control/fan-pid-control.py` for automatic temperature maintenance:
```bash
# Gaming: Keep cool with higher fan range
sudo ./pid_control/fan-pid-control.py 40 100 65

# Office work: Quiet with higher temp
sudo ./pid_control/fan-pid-control.py 20 60 75

# Compiling: Balance performance and noise
sudo ./pid_control/fan-pid-control.py 35 80 70
```

### Scenario 3: Background Service
Run PID controller as a systemd service (optional):

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

## Warning

**Do not run tccd and these utilities simultaneously.** They will compete for fan control.

To disable tccd:
```bash
sudo systemctl stop tccd
sudo systemctl disable tccd  # Optional: prevent auto-start
```

To re-enable tccd:
```bash
sudo systemctl enable tccd
sudo systemctl start tccd
```

## Hardware Details

- **Device**: `/dev/tuxedo_io`
- **Interface**: Clevo ACPI
- **Model**: Gemini Gen2 (SIRIUS1601/SIRIUS1602)
- **Fans**: 2 fans (CPU and GPU)
- **Speed range**: 0-255 (0-100%)

## Troubleshooting

### PID controller oscillates
- Reduce Kp (proportional gain)
- Increase Kd (derivative gain)
- Adjust target temperature closer to natural idle

### Fans too aggressive
- Lower max_speed parameter
- Reduce Kp gain
- Increase target temperature

### Fans too slow to respond
- Increase Kp gain
- Increase Ki gain
- Lower min_speed to allow more range

### Temperature overshoots
- Increase Kd (derivative gain)
- Reduce Kp gain

## License

GPLv3 - Same as tuxedo-control-center

## Credits

Fan control implementation based on tuxedo-control-center and tuxedo-drivers.
