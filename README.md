## Goal

Quiet laptop for software development.

## What

- Direct fan control utility.
- PID-based automatic fan controller to maintain target temperature at a pre-defined fan speed range.
- Cpu profile that provides good performance/efficiency tradeoff at a limited TPU. 

## Why

Because the default tuxedo/intel power and cooling management stack is just unsatisfactory - loud, inefficient, providing unsatisfactory cpu performance for blocking tasks (like compilation - these are often limited by singlethread work) while often unexpectedly driving fans into sudden vacuum-cleaner spikes just because of background tasks that could happily run at efficient cores (like codebase indexing).

## How

- Maintain 65-70°C temperature with fan speeds limited to 10% - 30% range using PID controller.
- Limit CPU package power using Intel RAPL (Running Average Power Limit) to control heat and noise while maintaining good performance.

## Tools

### 1. run.sh - Default do-all-for-me script

This script:

- Disables tccd (tuxedo-control-center daemon) for this session to prevent it fighting over CPU power settings and fan speeds
- Sets CPU power limit using RAPL
- Starts the PID fan speed controller

### 2. fanctl - Manual Fan Control

Located in `fan_control/fanctl.c` - Simple utility that allows reading and setting fan speeds directly without tccd.

```bash
cd fan_control
make
sudo ./fanctl status      # Show fan status
sudo ./fanctl set 0 50    # Set CPU fan to 50%
sudo ./fanctl auto        # Return to automatic control
```

See `fan_control/README.md` for detailed documentation.

### 3. rapl.sh - CPU Power Limit Control (Recommended)

Located in `cpu_profile/rapl.sh` - Controls CPU power consumption using Intel RAPL (Running Average Power Limit).

RAPL provides fine-grained power limiting at the package level, allowing all cores to run while staying within a power budget. This is more flexible than disabling cores and provides better performance/watt efficiency.

```bash
cd cpu_profile
sudo ./rapl.sh status    # Show current power limits
sudo ./rapl.sh 25        # Set 25W limit (very quiet, efficient)
sudo ./rapl.sh 35        # Set 35W limit (balanced)
sudo ./rapl.sh 45        # Set 45W limit (performance)
```

**Benefits over core limiting:**
- All cores remain active and can be used when needed
- Better single-threaded performance (no artificial frequency caps)
- More efficient power usage (CPU dynamically adjusts to stay within limit)
- Simpler management (one parameter vs. per-core frequency settings)

### 4. power_profile.sh - CPU Power Profile Script (Alternative)

Located in `cpu_profile/power_profile.sh` - Configures CPU power profiles by limiting active cores and frequencies. This is an alternative approach to RAPL limiting.

The suggested profile is quiet4, which sets:
- 4 performance cores to run at 3.2Ghz - for tasks that are blocked by single-thread performance
- 16 efficiency cores to run at 1.2Ghz - to provide multithreaded performance

```bash
cd cpu_profile
sudo ./power_profile.sh status       # Show current CPU configuration
sudo ./power_profile.sh quiet1       # 2 P-cores at 4000 MHz, 16 E-cores at 1200 MHz
sudo ./power_profile.sh quiet4       # 4 P-cores at 3200 MHz, 16 E-cores at 1200 MHz
sudo ./power_profile.sh quiet8       # 8 P-cores at 1600 MHz, 16 E-cores at 1200 MHz
sudo ./power_profile.sh performance  # All cores at maximum frequency
sudo ./power_profile.sh powersave    # All cores at minimum frequency
```

**Note:** RAPL limiting (rapl.sh) is now preferred over core limiting for most use cases.

_Here ends the human-produced text. Rest is machine-generated._

### 5. fan-pid-control.py - PID Temperature Controller

Automatic fan controller that maintains a target temperature using a PID algorithm.

```bash
# Usage: sudo ./pid_control/fan-pid-control.py [-t] [-i interval] [min_speed% max_speed% target_temp°C]

# Example: Use defaults from config.py
sudo ./pid_control/fan-pid-control.py

# Example: Maintain 70°C with fan speeds between 10-30%
sudo ./pid_control/fan-pid-control.py 10 30 70

# Example with custom update interval (2 Hz = 0.5 second interval)
sudo ./pid_control/fan-pid-control.py -i 0.5 10 30 70
```

**Features:**
- Runs continuously (default 0.5s interval, configurable with `-i` flag)
- PID controller automatically adjusts fan speeds
- Dual temperature sources (fast coretemp + slow fanctl sensors)
- Multi-level exponential smoothing to prevent oscillations
- Sets both CPU and GPU fans to same speed
- Graceful shutdown on Ctrl+C (returns to auto mode)
- Real-time status display with PID terms in both physical and percentage units

**Example output:**
```
======================================================================
PID Fan Controller
======================================================================
Target temperature: 65°C
Fan speed range: 10% - 30%
Update interval: 0.5s (2.0 Hz)
PID parameters: Kp=3.0, Ki=0.2, Kd=10.0

Press Ctrl+C to stop and return to automatic control
======================================================================

66.0°C (pkg: 65.5 fan: 66.5) | Tgt: 65.0°C | Err: +1.0°C | Fan: 22.5% | PID +1.0 +0.5 +0.2 °C | PID: +3.0 +0.1 +2.0 %fanspeed
67.0°C (pkg: 67.0 fan: 67.0) | Tgt: 65.0°C | Err: +2.0°C | Fan: 24.8% | PID +2.0 +1.2 +0.5 °C | PID: +6.0 +0.2 +5.0 %fanspeed
```

**PID Parameters:**
- **Kp (Proportional)**: 3.0 - Increase fan 3% per degree above target
- **Ki (Integral)**: 0.2 - Gradual correction of steady-state error (one-sided: only accumulates when temp > target)
- **Kd (Derivative)**: 10.0 - Responds to rate of temperature change, increasing fan 10% per °C/s temperature rise

These can be adjusted in `pid_control/config.py` if needed.

**How the controller works:**
- **P term**: Reacts to current error (temp - target)
- **I term**: Accumulates error over time to eliminate steady-state offset (one-sided: cooling only)
- **D term**: Responds to rate of temperature change for immediate reaction to rising temps

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
- Reduce Kd (derivative gain)
- Increase smoothing half-lives in config.py (FANSPEED_HALFLIFE, D_TERM_HALFLIFE)
- Adjust target temperature closer to natural idle

### Fans too aggressive
- Lower max_speed parameter
- Reduce Kp gain
- Reduce Kd gain
- Increase target temperature

### Fans too slow to respond
- Increase Kp gain
- Increase Kd gain
- Decrease smoothing half-lives in config.py
- Lower min_speed to allow more range

### Temperature overshoots
- Reduce Kd (derivative gain)
- Reduce Kp gain
- Increase FANSPEED_HALFLIFE for slower fan speed changes

### Steady-state error (temp settles away from target)
- Increase Ki (integral gain) in config.py (currently 0.2)
- Check ONE_SIDED_INTEGRAL setting - if False, provides bidirectional averaging

## License

GPLv3 - Same as tuxedo-control-center

## Credits

Fan control implementation based on tuxedo-control-center and tuxedo-drivers.
