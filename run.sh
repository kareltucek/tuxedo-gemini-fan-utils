#!/bin/bash

cd $(dirname "$0")

sudo systemctl stop tccd 

# sudo ./cpu_profile/power_profile.sh quiet4

function officeSetup() {
    sudo ./cpu_profile/power_profile.sh balanced 
    sudo ./cpu_profile/rapl.sh 64
    sudo ./pid_control/fan-pid-control.py 10 25 70
}

function homeSetup() {
    sudo ./cpu_profile/power_profile.sh balanced 
    sudo ./cpu_profile/rapl.sh 32
    sudo ./pid_control/fan-pid-control.py 10 20 75
}

case "$1" in
    office)
        officeSetup
        ;;
    home)
        homeSetup
        ;;
    help)
        echo "Usage: $0 {office|home}"
        exit 1
        ;;
    *)
        if isHome 
        then
            homeSetup
        else
            officeSetup
        fi
        ;;
esac

