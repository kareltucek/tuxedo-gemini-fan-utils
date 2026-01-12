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
    KP = 2.0

    # Ki: Integral gain - higher = faster elimination of steady-state error
    # Default: 0.2 provides gradual correction of persistent offset
    # One-sided: only accumulates when temp > target (cooling control)
    KI = 0.2

    # Kd: Derivative gain - responds to rate of temperature change
    # Default: 5.0 means increase fan 5% per degree/second temperature rise
    # Provides immediate response when temperature is rising
    KD = 10.0

    # Integral behavior
    # ONE_SIDED_INTEGRAL: If True, integral only accumulates when temp > target (cooling only)
    #                     If False, integral is bidirectional (provides averaging/stabilization)
    #
    # This makes sense only with high integral gain. Otherwise it will always be overpowered
    # by the derivative gain when we need to start cooling quickly because of rising temp.
    ONE_SIDED_INTEGRAL = False


class ControlConfig:
    """Default control parameters"""

    # Fan speed range (percentage)
    MIN_SPEED = 10
    MAX_SPEED = 30

    # Target temperature (Celsius)
    TARGET_TEMP = 70

    # Control loop update interval (seconds)
    UPDATE_INTERVAL = 0.5


class SmoothingConfig:
    """Exponential smoothing configuration"""

    # All smoothing uses exponential moving average with specified half-life
    # Formula: alpha = 0.5^(dt/HALFLIFE)
    # Larger half-life = more smoothing = slower response

    # Coretemp package temperature smoothing (seconds)
    # Smooths rapid CPU package temp fluctuations from coretemp sensor
    CORETEMP_HALFLIFE = 1.0

    # Fanctl temperature sensor smoothing (seconds)
    # Smooths fanctl sensor readings (which update slowly ~1-2 Hz)
    FANCTL_TEMP_HALFLIFE = 2.0

    # D term smoothing (seconds)
    # Smooths derivative term oscillations
    D_TERM_HALFLIFE = 2

    # Fan speed smoothing (seconds)
    # Smooths fan speed commands to prevent rapid changes
    FANSPEED_HALFLIFE = 4


class ValidationConfig:
    """Input validation limits"""

    # Temperature range limits (Celsius)
    MIN_TEMP = 20
    MAX_TEMP = 95

    # Fan speed range limits (percentage)
    MIN_SPEED = 0
    MAX_SPEED = 100


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
