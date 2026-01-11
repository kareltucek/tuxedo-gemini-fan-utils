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
        self.prev_t_term = 0.0  # Track T term for decay when temp unchanged
        self.prev_d_term = 0.0  # Track D term for decay when temp unchanged
        self.time_since_temp_change = 0.0  # Accumulate time since temp last changed

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
        # Clamp integral to [0, max_integral] for cooling control
        # Non-negative prevents reducing fan speed when temp is below target
        max_integral = (self.max_output - self.min_output) / self.ki if self.ki != 0 else 1000
        self.integral = max(0, min(max_integral, self.integral))
        i_term = self.ki * self.integral

        # Derivative term on error
        # Note: d(error)/dt = d(temp - target)/dt = d(temp)/dt (target is constant)
        # So D and T are mathematically equivalent and should be handled identically
        if self.prev_temp is not None:
            if current_value != self.prev_temp:
                # Temperature changed - calculate derivative using accumulated time
                accumulated_dt = self.time_since_temp_change + dt
                if accumulated_dt > 0.1:  # Skip if too small
                    d_term = self.kd * (error - self.prev_error) / accumulated_dt
                else:
                    d_term = 0
            else:
                # Temperature unchanged - decay previous D term
                decay_factor = 0.8 ** dt
                d_term = self.prev_d_term * decay_factor
        else:
            d_term = 0

        # Temperature derivative term - responds to rate of temperature change
        # This provides immediate response to temperature changes regardless of position relative to setpoint
        if self.prev_temp is not None:
            # Check if temperature has actually changed
            if current_value != self.prev_temp:
                # Temperature changed - use accumulated time since last change
                self.time_since_temp_change += dt
                if self.time_since_temp_change > 0.1:  # Skip if too small
                    temp_rate = (current_value - self.prev_temp) / self.time_since_temp_change
                    t_term = self.kt * temp_rate
                    self.time_since_temp_change = 0.0  # Reset accumulator
                else:
                    t_term = 0
            else:
                # Temperature unchanged - accumulate time and decay previous T term
                self.time_since_temp_change += dt
                # Exponential decay: reduce by 20% per second
                decay_factor = 0.8 ** dt
                t_term = self.prev_t_term * decay_factor
        else:
            t_term = 0

        # Save state for next iteration
        self.prev_error = error
        self.prev_temp = current_value
        self.prev_d_term = d_term
        self.prev_t_term = t_term

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
        self.prev_d_term = 0.0
        self.prev_t_term = 0.0
        self.time_since_temp_change = 0.0
