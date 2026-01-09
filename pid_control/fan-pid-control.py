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

import subprocess
import sys
import time
import signal
import re
import os


class PIDController:
    """PID controller for fan speed regulation"""

    def __init__(self, kp, ki, kd, min_output, max_output):
        """
        Initialize PID controller

        Args:
            kp: Proportional gain
            ki: Integral gain
            kd: Derivative gain
            min_output: Minimum output value
            max_output: Maximum output value
        """
        self.kp = kp
        self.ki = ki
        self.kd = kd
        self.min_output = min_output
        self.max_output = max_output

        self.prev_error = 0.0
        self.integral = 0.0

    def compute(self, setpoint, current_value, dt):
        """
        Compute PID output

        Args:
            setpoint: Desired value (target temperature)
            current_value: Current measured value (current temperature)
            dt: Time delta since last computation (seconds)

        Returns:
            Control output (fan speed percentage)
        """
        # Calculate error
        error = current_value - setpoint

        # Proportional term
        p_term = self.kp * error

        # Integral term (with anti-windup)
        self.integral += error * dt
        # Clamp integral to prevent windup
        max_integral = (self.max_output - self.min_output) / self.ki if self.ki != 0 else 1000
        self.integral = max(-max_integral, min(max_integral, self.integral))
        i_term = self.ki * self.integral

        # Derivative term (skip on first iteration when dt is tiny)
        if dt > 0.1:  # Only compute derivative after first real iteration
            d_term = self.kd * (error - self.prev_error) / dt
        else:
            d_term = 0

        # Save error for next iteration
        self.prev_error = error

        # Calculate output
        output = p_term + i_term + d_term

        # Clamp output to min/max range
        if output < self.min_output:
            output = self.min_output
        elif output > self.max_output:
            output = self.max_output

        return output, p_term, i_term, d_term

    def reset(self):
        """Reset PID state"""
        self.prev_error = 0.0
        self.integral = 0.0


class FanController:
    """Interface to Tuxedo fan hardware using fanctl binary"""

    def __init__(self, fanctl_path, test_mode=False):
        self.fanctl_path = fanctl_path
        self.test_mode = test_mode

        # Check if fanctl exists
        if not os.path.exists(self.fanctl_path):
            print(f"ERROR: fanctl not found at {self.fanctl_path}", file=sys.stderr)
            print("Build it first: cd fan_control && make", file=sys.stderr)
            sys.exit(1)

    def _run_fanctl(self, *args):
        """Run fanctl command and return output"""
        try:
            result = subprocess.run(
                [self.fanctl_path] + list(args),
                capture_output=True,
                text=True,
                check=True
            )
            return result.stdout
        except subprocess.CalledProcessError as e:
            print(f"ERROR running fanctl: {e}", file=sys.stderr)
            print(f"Output: {e.stdout}", file=sys.stderr)
            print(f"Error: {e.stderr}", file=sys.stderr)
            sys.exit(1)
        except PermissionError:
            print(f"ERROR: Permission denied running {self.fanctl_path}", file=sys.stderr)
            print("Must run as root: sudo python3 fan-pid-control.py", file=sys.stderr)
            sys.exit(1)

    def read_fan_info(self, fan_num):
        """
        Read fan information using fanctl status

        Args:
            fan_num: Fan number (0 or 1)

        Returns:
            Tuple of (speed_pct, temp1, temp2)
        """
        output = self._run_fanctl('status')

        # Parse output looking for fan info
        # Example line: "  Speed: 35.3% (raw: 90/255)"
        # Example line: "  Temp2: 66°C"

        lines = output.split('\n')
        in_fan_section = False
        speed_pct = 0
        temp1 = 0
        temp2 = 0

        for line in lines:
            if f'Fan {fan_num}' in line:
                in_fan_section = True
                continue

            if in_fan_section:
                if line.strip() == '':
                    break

                # Parse speed line
                match = re.search(r'Speed:\s+([\d.]+)%', line)
                if match:
                    speed_pct = float(match.group(1))

                # Parse temp1 line
                match = re.search(r'Temp1:\s+(\d+)°C', line)
                if match:
                    temp1 = int(match.group(1))

                # Parse temp2 line
                match = re.search(r'Temp2:\s+(\d+)°C', line)
                if match:
                    temp2 = int(match.group(1))

        return speed_pct, temp1, temp2

    def set_fan_speed(self, fan_num, speed_pct):
        """
        Set fan speed using fanctl

        Args:
            fan_num: Fan number (0 or 1)
            speed_pct: Speed percentage (0-100)
        """
        if self.test_mode:
            # In test mode, don't actually set the speed
            return

        self._run_fanctl('set', str(fan_num), str(int(speed_pct)))

    def set_auto_mode(self):
        """Return fans to automatic control"""
        if self.test_mode:
            return

        self._run_fanctl('auto')


def main():
    # Parse arguments
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
    if not (0 <= min_speed_pct <= 100):
        print("ERROR: min_speed must be between 0 and 100", file=sys.stderr)
        sys.exit(1)
    if not (0 <= max_speed_pct <= 100):
        print("ERROR: max_speed must be between 0 and 100", file=sys.stderr)
        sys.exit(1)
    if not (20 <= target_temp <= 95):
        print("ERROR: target_temp should be between 20 and 95°C", file=sys.stderr)
        sys.exit(1)
    if min_speed_pct >= max_speed_pct:
        print("ERROR: min_speed must be less than max_speed", file=sys.stderr)
        sys.exit(1)

    # Locate fanctl binary (one level up, then into fan_control)
    script_dir = os.path.dirname(os.path.abspath(__file__))
    fanctl_path = os.path.join(script_dir, '..', 'fan_control', 'fanctl')

    # Initialize hardware interface
    fan_ctrl = FanController(fanctl_path, test_mode=test_mode)

    # PID tuning parameters (these may need adjustment)
    # Kp: Proportional gain - higher = more aggressive response to error
    # Ki: Integral gain - higher = faster elimination of steady-state error
    # Kd: Derivative gain - higher = more damping of oscillations
    kp = 3.0   # Increase fan speed by 3% per degree over target
    ki = 0.2   # Integral term for steady-state accuracy
    kd = 1.0   # Derivative term to dampen oscillations

    pid = PIDController(kp, ki, kd, min_speed_pct, max_speed_pct)

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

    print("=" * 70)
    print("PID Fan Controller" + (" [TEST MODE]" if test_mode else ""))
    print("=" * 70)
    print(f"Target temperature: {target_temp}°C")
    print(f"Fan speed range: {min_speed_pct}% - {max_speed_pct}%")
    print(f"PID parameters: Kp={kp}, Ki={ki}, Kd={kd}")
    if test_mode:
        print("\n*** TEST MODE: Speeds will be calculated but NOT applied ***")
    print()
    print("Press Ctrl+C to stop" + (" and return to automatic control" if not test_mode else ""))
    print("=" * 70)
    print()

    # Main control loop
    last_time = time.time()
    iteration = 0

    try:
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
            time.sleep(1.0)

    except KeyboardInterrupt:
        cleanup()
    except Exception as e:
        print(f"\nERROR: {e}", file=sys.stderr)
        cleanup()


if __name__ == '__main__':
    main()
