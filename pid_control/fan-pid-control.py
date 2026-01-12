#!/usr/bin/env python3
"""
PID-based fan controller for Tuxedo Gemini Gen2

Maintains target temperature using a PID (Proportional-Integral-Derivative) controller.
Runs continuously, adjusting fan speeds at specified interval.

Usage:
    sudo ./fan-pid-control.py [-t] [-i interval] [min_speed max_speed target_temp]

Arguments:
    -t              - Test mode (print suggested speeds without setting them)
    -i interval     - Update interval in seconds (default: from ControlConfig)
    min_speed       - Minimum fan speed percentage (optional, default: from ControlConfig)
    max_speed       - Maximum fan speed percentage (optional, default: from ControlConfig)
    target_temp     - Target CPU temperature in Celsius (optional, default: from ControlConfig)

Example:
    sudo ./fan-pid-control.py
    # Uses defaults from ControlConfig

    sudo ./fan-pid-control.py 30 100 70
    # Maintains CPU at 70°C, fan speed between 30-100%

    sudo ./fan-pid-control.py -i 0.5 30 100 70
    # Same but with custom update interval (0.5 second)

    sudo ./fan-pid-control.py -t
    # Test mode with defaults: shows what speeds would be set without actually setting them
"""

import sys
import time
import signal
import os

from pid_controller import PIDController
from fan_controller import FanController
from fanctl_temp_reader import FanctlTempReader
from coretemp_reader import CoretempReader
from config import PIDConfig, ControlConfig, ValidationConfig, validate_arguments


def parse_arguments():
    """
    Parse command-line arguments

    Returns:
        Tuple of (test_mode, interval, min_speed_pct, max_speed_pct, target_temp)
    """
    test_mode = False
    interval = ControlConfig.UPDATE_INTERVAL
    args = sys.argv[1:]

    # Check for test mode flag
    if args and args[0] == '-t':
        test_mode = True
        args = args[1:]

    # Check for interval flag
    if args and args[0] == '-i':
        if len(args) < 2:
            print("ERROR: -i flag requires interval value", file=sys.stderr)
            print(__doc__)
            sys.exit(1)
        try:
            interval = float(args[1])
            if interval <= 0 or interval > 10:
                print("ERROR: interval must be between 0 and 10 seconds", file=sys.stderr)
                sys.exit(1)
        except ValueError:
            print("ERROR: interval must be a number", file=sys.stderr)
            sys.exit(1)
        args = args[2:]

    # Parse control parameters (optional)
    if len(args) == 0:
        # Use defaults from ControlConfig
        min_speed_pct = ControlConfig.MIN_SPEED
        max_speed_pct = ControlConfig.MAX_SPEED
        target_temp = ControlConfig.TARGET_TEMP
    elif len(args) == 3:
        # Use provided values
        try:
            min_speed_pct = float(args[0])
            max_speed_pct = float(args[1])
            target_temp = float(args[2])
        except ValueError:
            print("ERROR: All arguments must be numbers", file=sys.stderr)
            print(__doc__)
            sys.exit(1)

        # Validate arguments
        is_valid, error_msg = validate_arguments(min_speed_pct, max_speed_pct, target_temp)
        if not is_valid:
            print(f"ERROR: {error_msg}", file=sys.stderr)
            sys.exit(1)
    else:
        print("ERROR: Provide either 0 or 3 control parameters (min_speed, max_speed, target_temp)", file=sys.stderr)
        print(__doc__)
        sys.exit(1)

    return test_mode, interval, min_speed_pct, max_speed_pct, target_temp


def locate_fanctl():
    """
    Locate the fanctl binary

    Returns:
        Path to fanctl binary
    """
    script_dir = os.path.dirname(os.path.abspath(__file__))
    fanctl_path = os.path.join(script_dir, '..', 'fan_control', 'fanctl')
    return fanctl_path


def print_header(test_mode, interval, min_speed_pct, max_speed_pct, target_temp):
    """Print startup header"""
    print("=" * 70)
    print("PID Fan Controller" + (" [TEST MODE]" if test_mode else ""))
    print("=" * 70)
    print(f"Target temperature: {target_temp}°C")
    print(f"Fan speed range: {min_speed_pct}% - {max_speed_pct}%")
    print(f"Update interval: {interval}s ({1.0/interval:.1f} Hz)")
    print(f"PID parameters: Kp={PIDConfig.KP}, Ki={PIDConfig.KI}, Kd={PIDConfig.KD}")
    if test_mode:
        print("\n*** TEST MODE: Speeds will be calculated but NOT applied ***")
    print()
    print("Press Ctrl+C to stop" + (" and return to automatic control" if not test_mode else ""))
    print("=" * 70)
    print()


def control_loop(fan_ctrl, read_temp_fn, pid, target_temp, interval, test_mode):
    """
    Main control loop

    Args:
        fan_ctrl: FanController instance
        read_temp_fn: Function that returns (combined_temp, cpu_package_temp, fanctl_max_temp)
        pid: PIDController instance
        target_temp: Target temperature
        interval: Update interval in seconds
        test_mode: Whether in test mode
    """
    last_time = time.time()
    iteration = 0

    while True:
        current_time = time.time()
        dt = current_time - last_time
        last_time = current_time

        # Read combined temperature
        current_temp, cpu_package_temp, fanctl_max_temp = read_temp_fn()

        # Compute PID output (handles temp change detection and D term decay internally)
        fan_speed_pct, raw_fan_speed, p_term, i_term, d_term = pid.compute(target_temp, current_temp, dt)

        # Set both fans to same speed
        fan_ctrl.set_fan_speed(0, fan_speed_pct)  # CPU fan
        fan_ctrl.set_fan_speed(1, fan_speed_pct)  # GPU fan

        # Display status every iteration
        iteration += 1
        error = current_temp - target_temp
        mode_indicator = "[TEST] " if test_mode else ""

        # Convert PID terms to temperature-equivalent contributions for display
        # All terms shown as "how many degrees of error would produce this contribution"
        p_input = p_term / PIDConfig.KP if PIDConfig.KP != 0 else 0
        i_input = i_term / PIDConfig.KP if PIDConfig.KP != 0 else 0  # Integral as temp-equivalent
        d_input = d_term / PIDConfig.KD if PIDConfig.KD != 0 else 0

        print(f"{mode_indicator}{current_temp:4.1f}°C (pkg:{cpu_package_temp:5.1f} fan:{fanctl_max_temp:5.1f}) | "
              f"Tgt: {target_temp:.1f}°C | "
              f"Err: {error:+5.1f}°C | "
              f"Fan: {raw_fan_speed:5.1f}% -> {fan_speed_pct:5.1f}% | "
              f"PID {p_input:+4.1f} {i_input:+4.1f} {d_input:+4.1f} °C | "
              f"PID: {p_term:+4.1f} {i_term:+4.1f} {d_term:+4.1f} %fanspeed")

        # Sleep until next iteration
        time.sleep(interval)


def main():
    """Main entry point"""
    # Parse command-line arguments
    test_mode, interval, min_speed_pct, max_speed_pct, target_temp = parse_arguments()

    # Locate fanctl binary
    fanctl_path = locate_fanctl()

    # Initialize hardware interface
    fan_ctrl = FanController(fanctl_path, test_mode=test_mode)

    # Initialize temperature readers
    fanctl_temp = FanctlTempReader(fanctl_path)
    coretemp = CoretempReader()

    # Create temperature reading function (combines both sources)
    def read_temp():
        cpu_package_temp = coretemp.read_temperature()
        fanctl_max_temp = fanctl_temp.read_max_temperature()
        combined_temp = (cpu_package_temp + fanctl_max_temp) / 2.0
        return combined_temp, cpu_package_temp, fanctl_max_temp

    # Initialize PID controller
    pid = PIDController(
        PIDConfig.KP,
        PIDConfig.KI,
        PIDConfig.KD,
        min_speed_pct,
        max_speed_pct
    )

    # Cleanup handler
    def cleanup(signum=None, frame=None):
        print("\n\nShutting down...")
        if not test_mode:
            print("Returning fans to automatic control...")
            fan_ctrl.set_auto_mode()
        else:
            print("Test mode - no cleanup needed")
        print("Done.")
        sys.exit(0)

    # Register signal handlers
    signal.signal(signal.SIGINT, cleanup)
    signal.signal(signal.SIGTERM, cleanup)

    # Print header
    print_header(test_mode, interval, min_speed_pct, max_speed_pct, target_temp)

    # Run control loop
    try:
        control_loop(fan_ctrl, read_temp, pid, target_temp, interval, test_mode)
    except KeyboardInterrupt:
        cleanup()
    except Exception as e:
        print(f"\nERROR: {e}", file=sys.stderr)
        cleanup()


if __name__ == '__main__':
    main()
