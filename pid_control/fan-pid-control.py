#!/usr/bin/env python3
"""
PID-based fan controller for Tuxedo Gemini Gen2

Maintains target temperature using a PID (Proportional-Integral-Derivative) controller.
Runs continuously, adjusting fan speeds once per second.

Usage:
    sudo ./fan-pid-control.py [-t] <min_speed> <max_speed> <target_temp>

Arguments:
    -t           - Test mode (print suggested speeds without setting them)
    min_speed    - Minimum fan speed percentage (0-100)
    max_speed    - Maximum fan speed percentage (0-100)
    target_temp  - Target CPU temperature in Celsius

Example:
    sudo ./fan-pid-control.py 30 100 70
    # Maintains CPU at 70°C, fan speed between 30-100%

    sudo ./fan-pid-control.py -t 30 100 70
    # Test mode: shows what speeds would be set without actually setting them
"""

import sys
import time
import signal
import os

from pid_controller import PIDController
from fan_controller import FanController
from config import PIDConfig, ValidationConfig, validate_arguments


def parse_arguments():
    """
    Parse command-line arguments

    Returns:
        Tuple of (test_mode, min_speed_pct, max_speed_pct, target_temp)
    """
    test_mode = False
    args = sys.argv[1:]

    # Check for test mode flag
    if args and args[0] == '-t':
        test_mode = True
        args = args[1:]

    if len(args) != 3:
        print(__doc__)
        sys.exit(1)

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

    return test_mode, min_speed_pct, max_speed_pct, target_temp


def locate_fanctl():
    """
    Locate the fanctl binary

    Returns:
        Path to fanctl binary
    """
    script_dir = os.path.dirname(os.path.abspath(__file__))
    fanctl_path = os.path.join(script_dir, '..', 'fan_control', 'fanctl')
    return fanctl_path


def print_header(test_mode, min_speed_pct, max_speed_pct, target_temp):
    """Print startup header"""
    print("=" * 70)
    print("PID Fan Controller" + (" [TEST MODE]" if test_mode else ""))
    print("=" * 70)
    print(f"Target temperature: {target_temp}°C")
    print(f"Fan speed range: {min_speed_pct}% - {max_speed_pct}%")
    print(f"PID parameters: Kp={PIDConfig.KP}, Ki={PIDConfig.KI}, Kd={PIDConfig.KD}")
    if test_mode:
        print("\n*** TEST MODE: Speeds will be calculated but NOT applied ***")
    print()
    print("Press Ctrl+C to stop" + (" and return to automatic control" if not test_mode else ""))
    print("=" * 70)
    print()


def control_loop(fan_ctrl, pid, target_temp, test_mode):
    """
    Main control loop

    Args:
        fan_ctrl: FanController instance
        pid: PIDController instance
        target_temp: Target temperature
        test_mode: Whether in test mode
    """
    last_time = time.time()
    iteration = 0

    while True:
        current_time = time.time()
        dt = current_time - last_time
        last_time = current_time

        # Read CPU temperature (fan 0 = CPU)
        current_speed_pct, temp1, temp2 = fan_ctrl.read_fan_info(0)
        current_temp = temp2  # temp2 is generally more reliable

        # Compute PID output
        fan_speed_pct, p_term, i_term, d_term = pid.compute(target_temp, current_temp, dt)

        # Set both fans to same speed
        fan_ctrl.set_fan_speed(0, fan_speed_pct)  # CPU fan
        fan_ctrl.set_fan_speed(1, fan_speed_pct)  # GPU fan

        # Display status every iteration
        iteration += 1
        error = current_temp - target_temp
        mode_indicator = "[TEST]" if test_mode else "[LIVE]"
        print(f"{mode_indicator} [{iteration:4d}] Temp: {current_temp:5.1f}°C | "
              f"Target: {target_temp:.1f}°C | "
              f"Error: {error:+5.1f}°C | "
              f"Fan: {fan_speed_pct:5.1f}% | "
              f"P:{p_term:+6.2f} I:{i_term:+6.2f} D:{d_term:+6.2f}")

        # Sleep until next iteration
        time.sleep(ValidationConfig.UPDATE_INTERVAL)


def main():
    """Main entry point"""
    # Parse command-line arguments
    test_mode, min_speed_pct, max_speed_pct, target_temp = parse_arguments()

    # Locate fanctl binary
    fanctl_path = locate_fanctl()

    # Initialize hardware interface
    fan_ctrl = FanController(fanctl_path, test_mode=test_mode)

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
    print_header(test_mode, min_speed_pct, max_speed_pct, target_temp)

    # Run control loop
    try:
        control_loop(fan_ctrl, pid, target_temp, test_mode)
    except KeyboardInterrupt:
        cleanup()
    except Exception as e:
        print(f"\nERROR: {e}", file=sys.stderr)
        cleanup()


if __name__ == '__main__':
    main()
