#!/usr/bin/env bash
set -e

MAP_PATH=${1:-data/maps/sample.osm}
LOG_PATH=${2:-data/raw_logs/synthetic_log.csv}

WORKSPACE="/home/subash/DiskD/RoboticsWorks/LaneLog"
PACKAGE_DIR="$WORKSPACE/src/lanelog_curator"

source /opt/ros/jazzy/setup.bash
source "$WORKSPACE/install/setup.bash"

cd "$PACKAGE_DIR"

ros2 run lanelog_curator lanelog_curator "$MAP_PATH" "$LOG_PATH"

