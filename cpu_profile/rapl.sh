#!/bin/bash

echo "Setting power limit to $1 watts"

echo $(($1 * 1000000)) | sudo tee /sys/class/powercap/intel-rapl:0/constraint_0_power_limit_uw > /dev/null

