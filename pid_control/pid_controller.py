"""
PID Controller implementation

Proportional-Integral-Derivative controller for temperature regulation.
"""


class PIDController:
    """PID controller for fan speed regulation"""

    def __init__(self, kp, ki, kd, kt, min_output, max_output):
        """
        Initialize PID controller

        Args:
            kp: Proportional gain
            ki: Integral gain
            kd: Derivative gain
            kt: Temperature derivative gain (responds to rate of temp change)
            min_output: Minimum output value
            max_output: Maximum output value
        """
        self.kp = kp
        self.ki = ki
        self.kd = kd
        self.kt = kt
        self.min_output = min_output
        self.max_output = max_output

        self.prev_error = 0.0
        self.prev_temp = None
        self.integral = 0.0

    def compute(self, setpoint, current_value, dt):
        """
        Compute PID output

        Args:
            setpoint: Desired value (target temperature)
            current_value: Current measured value (current temperature)
            dt: Time delta since last computation (seconds)

        Returns:
            Tuple of (output, p_term, i_term, d_term, t_term)
                output: Control output (fan speed percentage)
                p_term: Proportional term contribution
                i_term: Integral term contribution
                d_term: Derivative term contribution
                t_term: Temperature derivative term contribution
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

        # Derivative term on error (skip on first iteration when dt is tiny)
        if dt > 0.1:  # Only compute derivative after first real iteration
            d_term = self.kd * (error - self.prev_error) / dt
        else:
            d_term = 0

        # Temperature derivative term - responds to rate of temperature change
        # This provides immediate response to temperature changes regardless of position relative to setpoint
        if self.prev_temp is not None and dt > 0.1:
            temp_rate = (current_value - self.prev_temp) / dt
            # Positive temp_rate (rising temp) increases fan speed
            t_term = self.kt * temp_rate
        else:
            t_term = 0

        # Save state for next iteration
        self.prev_error = error
        self.prev_temp = current_value

        # Calculate output
        output = p_term + i_term + d_term + t_term

        # Clamp output to min/max range
        if output < self.min_output:
            output = self.min_output
        elif output > self.max_output:
            output = self.max_output

        return output, p_term, i_term, d_term, t_term

    def reset(self):
        """Reset PID state"""
        self.prev_error = 0.0
        self.prev_temp = None
        self.integral = 0.0
