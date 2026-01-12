"""
PID Controller implementation

Proportional-Integral-Derivative controller for temperature regulation.
"""

from config import SmoothingConfig, PIDConfig


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
        self.prev_output = None  # Previous clamped output for anti-windup

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

        # Derivative term on error (calculate before integral for anti-windup)
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
        # If half-life is 0, disable smoothing (for debugging)
        if SmoothingConfig.D_TERM_HALFLIFE == 0:
            d_term = raw_d_term
        else:
            alpha = pow(0.5, dt / SmoothingConfig.D_TERM_HALFLIFE)
            self.smoothed_d_term = alpha * self.smoothed_d_term + (1 - alpha) * raw_d_term
            # Scale by 2/half_life to compensate for averaging effect (maintains proper gain)
            d_term = self.smoothed_d_term * (2.0 / SmoothingConfig.D_TERM_HALFLIFE)

        # Integral term with dynamic limit based on P+D contribution
        # The integral should only fill the remaining headroom to limits
        base_speed = (self.min_output + self.max_output) / 2.0

        # Calculate what output would be without integral term
        output_without_i = base_speed + p_term + d_term

        # Determine integral limits based on remaining headroom
        if self.ki != 0:
            max_i_contribution = self.max_output - output_without_i
            min_i_contribution = self.min_output - output_without_i
            max_integral = max_i_contribution / self.ki
            min_integral = min_i_contribution / self.ki

            # Ensure integral always has at least quarter range available
            # This allows it to stabilize at edge values even when P+D saturate
            quarter_range_integral = (self.max_output - self.min_output) / 4.0 / self.ki
            max_integral = max(max_integral, quarter_range_integral)
            min_integral = min(min_integral, -quarter_range_integral)

            # Clamp limits to prevent inversion
            # min_integral shouldn't go above 0 (can't force integral positive)
            min_integral = min(min_integral, 0)
            # max_integral shouldn't go below 0 (can't force integral negative)
            max_integral = max(max_integral, 0)

            if PIDConfig.ONE_SIDED_INTEGRAL:
                # One-sided: integral can't go negative at all
                min_integral = 0
        else:
            max_integral = 1000
            min_integral = 0 if PIDConfig.ONE_SIDED_INTEGRAL else -1000

        # Conditional integration: only accumulate if previous output wasn't saturated in that direction
        # This prevents windup when output is at limits (including after smoothing)
        if self.prev_output is not None:
            # Use a small epsilon for saturation detection
            epsilon = 0.1
            at_max = self.prev_output >= (self.max_output - epsilon)
            at_min = self.prev_output <= (self.min_output + epsilon)

            if error > 0 and at_max:
                # Previous output saturated at max, don't accumulate upward
                pass
            elif error < 0 and at_min:
                # Previous output saturated at min, don't accumulate downward
                pass
            else:
                # Not saturated, accumulate normally
                self.integral += error * dt
                # Clamp to limits
                self.integral = max(min_integral, min(max_integral, self.integral))
        else:
            # First iteration, accumulate normally
            self.integral += error * dt
            self.integral = max(min_integral, min(max_integral, self.integral))

        i_term = self.ki * self.integral

        # Save state for next iteration
        self.prev_error = error
        self.prev_temp = current_value
        self.prev_d_term = raw_d_term

        # Calculate output
        # Base speed is midpoint of range, PID terms modulate around it
        raw_output = base_speed + p_term + i_term + d_term

        # Clamp raw output to min/max range BEFORE smoothing
        # This prevents smoothing windup when output saturates
        raw_output_clamped = raw_output
        if raw_output_clamped < self.min_output:
            raw_output_clamped = self.min_output
        elif raw_output_clamped > self.max_output:
            raw_output_clamped = self.max_output

        # Apply exponential smoothing to CLAMPED output
        # This prevents wild fan speed oscillations
        # If half-life is 0, disable smoothing (for debugging)
        if SmoothingConfig.FANSPEED_HALFLIFE == 0:
            output = raw_output_clamped
        else:
            if self.smoothed_output is None:
                self.smoothed_output = raw_output_clamped
            else:
                alpha = pow(0.5, dt / SmoothingConfig.FANSPEED_HALFLIFE)
                self.smoothed_output = alpha * self.smoothed_output + (1 - alpha) * raw_output_clamped
            output = self.smoothed_output

        # Final clamp (should be redundant but ensures output is always in range)
        if output < self.min_output:
            output = self.min_output
        elif output > self.max_output:
            output = self.max_output

        # Save clamped output for anti-windup check on next iteration
        self.prev_output = output

        return output, raw_output_clamped, p_term, i_term, d_term

    def reset(self):
        """Reset PID state"""
        self.prev_error = 0.0
        self.prev_temp = None
        self.integral = 0.0
        self.prev_d_term = 0.0
        self.smoothed_d_term = 0.0
        self.smoothed_output = None
        self.time_since_temp_change = 0.0
        self.prev_output = None
