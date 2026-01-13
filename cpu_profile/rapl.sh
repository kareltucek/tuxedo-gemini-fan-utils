#!/bin/bash
#
# RAPL Power Limit Control
# Sets Intel RAPL (Running Average Power Limit) for CPU package power management
#
# Usage: ./rapl.sh <watts> | status
#
# Examples:
#   ./rapl.sh 35       # Set CPU power limit to 35 watts
#   ./rapl.sh 25       # Set CPU power limit to 25 watts (quiet)
#   ./rapl.sh 45       # Set CPU power limit to 45 watts (performance)
#   ./rapl.sh status   # Show current power limit
#
# This sets all three RAPL constraints (PL1, PL2, and extended) to the same value.
# RAPL limits the total package power consumption (all cores + uncore).

show_help() {
    echo "RAPL Power Limit Control"
    echo ""
    echo "Usage: $0 <watts> | status"
    echo ""
    echo "Commands:"
    echo "  <watts>   Set CPU power limit to specified watts (e.g., 25, 35, 45)"
    echo "  status    Show current power limit settings"
    echo ""
    echo "Examples:"
    echo "  $0 35       # Set 35W limit (balanced)"
    echo "  $0 25       # Set 25W limit (quiet, efficient)"
    echo "  $0 45       # Set 45W limit (performance)"
    echo ""
    echo "RAPL (Running Average Power Limit) controls the total CPU package power"
    echo "consumption. Lower values = cooler, quieter, more efficient."
    echo "Higher values = more performance, more heat, more fan noise."
}

show_status() {
    echo "Current RAPL Power Limits:"
    echo ""
    local constraint_0=$(cat /sys/class/powercap/intel-rapl:0/constraint_0_power_limit_uw)
    local constraint_1=$(cat /sys/class/powercap/intel-rapl:0/constraint_1_power_limit_uw)
    local constraint_2=$(cat /sys/class/powercap/intel-rapl:0/constraint_2_power_limit_uw)

    echo "  Constraint 0 (PL1 - long term):  $((constraint_0 / 1000000)) W"
    echo "  Constraint 1 (PL2 - short term): $((constraint_1 / 1000000)) W"
    echo "  Constraint 2 (extended):         $((constraint_2 / 1000000)) W"
}

if [ $# -eq 0 ] || [ "$1" = "-h" ] || [ "$1" = "--help" ]; then
    show_help
    exit 0
fi

if [ "$1" = "status" ]; then
    show_status
    exit 0
fi

# Validate input is a number
if ! [[ "$1" =~ ^[0-9]+$ ]]; then
    echo "Error: Power limit must be a positive integer (watts)"
    echo ""
    show_help
    exit 1
fi

echo "Setting power limit to $1 watts"

echo $(($1 * 1000000)) | sudo tee /sys/class/powercap/intel-rapl:0/constraint_0_power_limit_uw > /dev/null
echo $(($1 * 1000000)) | sudo tee /sys/class/powercap/intel-rapl:0/constraint_1_power_limit_uw > /dev/null
echo $(($1 * 1000000)) | sudo tee /sys/class/powercap/intel-rapl:0/constraint_2_power_limit_uw > /dev/null

echo "Power limit set successfully"
echo ""
show_status
