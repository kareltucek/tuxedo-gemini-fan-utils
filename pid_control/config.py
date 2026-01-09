"""
Configuration for PID fan controller

PID tuning parameters and default settings.
"""


class PIDConfig:
    """PID controller configuration"""

    # PID tuning parameters
    # These can be adjusted for different response characteristics

    # Kp: Proportional gain - higher = more aggressive response to error
    # Default: 3.0 means increase fan speed by 3% per degree over target
    KP = 3.0

    # Ki: Integral gain - higher = faster elimination of steady-state error
    # Default: 0.2 provides gradual correction of persistent offset
    KI = 0.2

    # Kd: Derivative gain - higher = more damping of oscillations
    # Default: 1.0 provides moderate damping
    KD = 1.0

    # Kt: Temperature derivative gain - responds to rate of temperature change
    # This makes the controller react immediately to temperature changes
    # Default: 5.0 means increase fan 5% per degree/second temperature rise
    KT = 5.0


class ValidationConfig:
    """Input validation limits"""

    # Temperature range limits (Celsius)
    MIN_TEMP = 20
    MAX_TEMP = 95

    # Fan speed range limits (percentage)
    MIN_SPEED = 0
    MAX_SPEED = 100

    # Control loop update rate (seconds)
    UPDATE_INTERVAL = 1.0


def validate_arguments(min_speed_pct, max_speed_pct, target_temp):
    """
    Validate command-line arguments

    Args:
        min_speed_pct: Minimum fan speed percentage
        max_speed_pct: Maximum fan speed percentage
        target_temp: Target temperature

    Returns:
        Tuple of (is_valid, error_message)
            is_valid: True if all arguments are valid
            error_message: Error description if invalid, None otherwise
    """
    if not (ValidationConfig.MIN_SPEED <= min_speed_pct <= ValidationConfig.MAX_SPEED):
        return False, f"min_speed must be between {ValidationConfig.MIN_SPEED} and {ValidationConfig.MAX_SPEED}"

    if not (ValidationConfig.MIN_SPEED <= max_speed_pct <= ValidationConfig.MAX_SPEED):
        return False, f"max_speed must be between {ValidationConfig.MIN_SPEED} and {ValidationConfig.MAX_SPEED}"

    if not (ValidationConfig.MIN_TEMP <= target_temp <= ValidationConfig.MAX_TEMP):
        return False, f"target_temp should be between {ValidationConfig.MIN_TEMP} and {ValidationConfig.MAX_TEMP}°C"

    if min_speed_pct >= max_speed_pct:
        return False, "min_speed must be less than max_speed"

    return True, None
