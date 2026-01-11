"""
PID Controller implementation

Proportional-Integral-Derivative controller for temperature regulation.
"""

from config import SmoothingConfig


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
        self.prev_temp = None
        self.integral = 0.0
        self.prev_d_term = 0.0  # Track D term for decay when temp unchanged
        self.smoothed_d_term = 0.0  # Smoothed D term output (1-second half-life)
        self.smoothed_output = None  # Smoothed final output (1-second half-life)
        self.time_since_temp_change = 0.0  # Accumulate time since temp last changed

    def compute(self, setpoint, current_value, dt):
        """
        Compute PID output

        Args:
            setpoint: Desired value (target temperature)
            current_value: Current measured value (current temperature)
            dt: Time delta since last computation (seconds)

        Returns:
            Tuple of (output, p_term, i_term, d_term)
                output: Control output (fan speed percentage)
                p_term: Proportional term contribution
                i_term: Integral term contribution
                d_term: Derivative term contribution
        """
        # Calculate error
        error = current_value - setpoint

        # Proportional term
        p_term = self.kp * error

        # Integral term (with anti-windup)
        self.integral += error * dt
        # Clamp integral to [0, max_integral] for cooling control
        # Non-negative prevents reducing fan speed when temp is below target
        max_integral = (self.max_output - self.min_output) / self.ki if self.ki != 0 else 1000
        self.integral = max(0, min(max_integral, self.integral))
        i_term = self.ki * self.integral

        # Derivative term on error
        # Note: d(error)/dt = d(temp - target)/dt = d(temp)/dt (target is constant)
        # Responds to rate of temperature change for immediate response
        if self.prev_temp is not None:
            if current_value != self.prev_temp:
                # Temperature changed - calculate derivative using accumulated time
                self.time_since_temp_change += dt
                if self.time_since_temp_change > 0.1:  # Skip if too small
                    raw_d_term = self.kd * (error - self.prev_error) / self.time_since_temp_change
                    self.time_since_temp_change = 0.0  # Reset accumulator
                else:
                    raw_d_term = self.prev_d_term  # Keep previous value
            else:
                # Temperature unchanged - accumulate time and decay previous D term
                self.time_since_temp_change += dt
                # Exponential decay: reduce by 20% per second
                decay_factor = 0.8 ** dt
                raw_d_term = self.prev_d_term * decay_factor
        else:
            raw_d_term = 0

        # Apply exponential smoothing to D term with configured half-life
        # This reduces oscillations while preserving trend
        alpha = pow(0.5, dt / SmoothingConfig.D_TERM_HALFLIFE)
        self.smoothed_d_term = alpha * self.smoothed_d_term + (1 - alpha) * raw_d_term
        d_term = self.smoothed_d_term

        # Save state for next iteration
        self.prev_error = error
        self.prev_temp = current_value
        self.prev_d_term = raw_d_term

        # Calculate output
        # Base speed is midpoint of range, PID terms modulate around it
        base_speed = (self.min_output + self.max_output) / 2.0
        raw_output = base_speed + p_term + i_term + d_term

        # Apply exponential smoothing to output with configured half-life
        # This prevents wild fan speed oscillations
        if self.smoothed_output is None:
            self.smoothed_output = raw_output
        else:
            alpha = pow(0.5, dt / SmoothingConfig.FANSPEED_HALFLIFE)
            self.smoothed_output = alpha * self.smoothed_output + (1 - alpha) * raw_output

        output = self.smoothed_output

        # Clamp output to min/max range
        if output < self.min_output:
            output = self.min_output
        elif output > self.max_output:
            output = self.max_output

        return output, p_term, i_term, d_term

    def reset(self):
        """Reset PID state"""
        self.prev_error = 0.0
        self.prev_temp = None
        self.integral = 0.0
        self.prev_d_term = 0.0
        self.smoothed_d_term = 0.0
        self.smoothed_output = None
        self.time_since_temp_change = 0.0
