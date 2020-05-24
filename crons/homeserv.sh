#!/usr/bin/env bash

# VARIABLES
SCRIPTS=extras/server-tools/scripts
PY3=/home/bobrock/venvs/stools/bin/python3

# LOG ANALYSIS
0 */4 * * *         $PY3    $HOME/$SCRIPTS/log_reader.py
32 3 20 * *         $PY3    $HOME/$SCRIPTS/log_remover.py -lvl debug
# PIHOLE
33 8 * * *          $PY3    $HOME/$SCRIPTS/net/unknown_ip_monitor.py

# MYSQL
30 6 * * *          $PY3    $HOME/$SCRIPTS/grafana/grafana.py
# SYS DATA COLLECTION
*/10 * * * *        $PY3    $HOME/$SCRIPTS/net/machine_uptime.py
*/5 * * * *         $PY3    $HOME/$SCRIPTS/net/machine_connected.py
0 */3 * * *         $PY3    $HOME/$SCRIPTS/speedtest/speedtest_logger.py
# ENV DATA COLECTION
*/10 * * * *        $PY3    $HOME/$SCRIPTS/temps/ecobee_temps.py
20 19 * * *         $PY3    $HOME/$SCRIPTS/temps/frost_warning.py
*/10 * * * *        $PY3    $HOME/$SCRIPTS/temps/severe_weather_check.py
17 16 * * 1-5       $PY3    $HOME/$SCRIPTS/temps/significant_temp_change_warning.py
# HOME AUTOMATION
*/10 03-22 * * *    $PY3    $HOME/$SCRIPTS/camera/amcrest_notify_zone.py
5 23 * * *          $PY3    $HOME/$SCRIPTS/camera/amcrest_nighttime.py
# SLACK
15 */4 * * *        $PY3    $HOME/$SCRIPTS/slackbot/slack_logger.py

# Vpulse Automation
#40 03 * * * export DISPLAY=:0; $PY3 $HOME/$SENSORS/vpulse/vpulse_auto.py -lvl debug
