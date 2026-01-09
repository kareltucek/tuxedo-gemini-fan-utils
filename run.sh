#!/bin/bash

sudo systemctl stop tccd 

sudo ./cpu_profile/power_profile.sh quiet4

sudo ./pid_control/fan-pid-control.py 10 30 65

