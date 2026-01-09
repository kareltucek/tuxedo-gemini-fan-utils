"""
PID Fan Controller Package

Automatic temperature-based fan control for Tuxedo Gemini Gen2 laptops.
"""

__version__ = '1.0.0'
__author__ = 'Tuxedo Gemini Gen2 Fan Control Project'

from .pid_controller import PIDController
from .fan_controller import FanController
from .config import PIDConfig, ValidationConfig, validate_arguments

__all__ = [
    'PIDController',
    'FanController',
    'PIDConfig',
    'ValidationConfig',
    'validate_arguments',
]
