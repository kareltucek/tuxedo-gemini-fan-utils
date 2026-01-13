#!/bin/bash

# powerProfile - Manage CPU power profiles for i9-13900HX
# Usage: powerProfile [profile_name]
#
# Profiles:
#   quietTux (default) - 1 P-core @ max, 16 E-cores @ 1200 MHz
#   performance        - All cores @ max frequency
#   powersave          - All cores @ min frequency

# CPU topology for i9-13900HX:
# - P-cores (8 cores, 16 threads): CPUs 0-15
#   - Core 0: CPUs 0-1
#   - Core 1: CPUs 2-3
#   - ...
#   - Core 7: CPUs 14-15
# - E-cores (16 cores, 16 threads): CPUs 16-31

readonly CPU_BASE="/sys/devices/system/cpu"
readonly MAX_FREQ_MHZ=5400
readonly MIN_FREQ_MHZ=800

# Check if running as root
if [ "$EUID" -ne 0 ]; then
    echo "Error: This script must be run as root" >&2
    echo "Usage: sudo $0 [profile_name]" >&2
    exit 1
fi

# Helper functions
set_cpu_online() {
    local cpu=$1
    local state=$2  # 0 or 1

    # CPU 0 cannot be disabled
    if [ "$cpu" -eq 0 ]; then
        return
    fi

    local online_file="$CPU_BASE/cpu$cpu/online"
    if [ -w "$online_file" ]; then
        echo "$state" > "$online_file" 2>/dev/null
    fi
}

set_cpu_freq() {
    local cpu=$1
    local freq_mhz=$2
    local freq_khz=$((freq_mhz * 1000))

    local max_freq_file="$CPU_BASE/cpu$cpu/cpufreq/scaling_max_freq"
    local min_freq_file="$CPU_BASE/cpu$cpu/cpufreq/scaling_min_freq"

    if [ -w "$max_freq_file" ]; then
        echo "$freq_khz" > "$max_freq_file" 2>/dev/null
    fi

    # Also set min freq to allow reaching the target
    if [ -w "$min_freq_file" ]; then
        echo "$MIN_FREQ_MHZ"000 > "$min_freq_file" 2>/dev/null
    fi
}

enable_cpu_range() {
    local start=$1
    local end=$2
    local freq_mhz=$3

    for cpu in $(seq $start $end); do
        set_cpu_online "$cpu" 1
        sleep 0.01  # Brief delay for CPU to come online
        set_cpu_freq "$cpu" "$freq_mhz"
    done
}

disable_cpu_range() {
    local start=$1
    local end=$2

    for cpu in $(seq $start $end); do
        set_cpu_online "$cpu" 0
    done
}

# Show current CPU status
show_status() {
    echo "Current CPU Status:"
    echo "==================="

    local online_count=0
    for cpu in {0..31}; do
        local online_file="$CPU_BASE/cpu$cpu/online"
        if [ "$cpu" -eq 0 ] || [ -f "$online_file" ]; then
            if [ "$cpu" -eq 0 ] || [ "$(cat "$online_file" 2>/dev/null)" = "1" ]; then
                online_count=$((online_count + 1))
                local freq_file="$CPU_BASE/cpu$cpu/cpufreq/scaling_max_freq"
                if [ -r "$freq_file" ]; then
                    local freq_khz=$(cat "$freq_file")
                    local freq_mhz=$((freq_khz / 1000))
                    local type="P"
                    [ "$cpu" -ge 16 ] && type="E"
                    echo "  CPU $cpu ($type-core): online, max ${freq_mhz} MHz"
                fi
            fi
        fi
    done
    echo ""
    echo "Total online: $online_count / 32 CPUs"
}

# Main
profile="${1:-quietTux}"

case "$profile" in
    quiet1)
        enable_cpu_range 0 0 "$MAX_FREQ_MHZ"
        disable_cpu_range 1 15
        enable_cpu_range 16 31 1200
        ;;
    quiet1)
        enable_cpu_range 0 1 "4000"
        disable_cpu_range 2 15
        enable_cpu_range 16 31 1200
        ;;
    quiet4)
        enable_cpu_range 0 3 "3200"
        disable_cpu_range 4 15
        enable_cpu_range 16 31 1200
        ;;
    quiet8)
        enable_cpu_range 0 7 "1600"
        disable_cpu_range 8 15
        enable_cpu_range 16 31 1200
        ;;
    performance)
        enable_cpu_range 0 31 "$MAX_FREQ_MHZ"
        ;;
    powersave)
        enable_cpu_range 0 31 "$MIN_FREQ_MHZ"
        ;;
    balanced)
        enable_cpu_range 0 31 "4000"
        ;;
    status)
        show_status
        exit 0
        ;;
    *)
        echo "Unknown profile: $profile" >&2
        echo "" >&2
        echo "Commands:" >&2
        echo "  status      - Show current CPU configuration" >&2
        exit 1
        ;;
esac

echo ""
show_status

