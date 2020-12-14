#!/usr/bin/env bash

# VARIABLES
SCRIPTS=extras/servertools/scripts
PY3=/home/bobrock/venvs/stools/bin/python3

# LOG ANALYSIS
#0 */4 * * *            $PY3    $HOME/$SCRIPTS/log_reader.py
#32 3 20 * *            $PY3    $HOME/$SCRIPTS/log_remover.py -lvl debug
## PIHOLE

# SYS DATA COLLECTION
*/2 * * * *             $PY3    $HOME/$SCRIPTS/net/machine-connected.py
0 */3 * * *             $PY3    $HOME/$SCRIPTS/net/speedtest-logger.py
## ENV DATA COLECTION
*/10 * * * *            $PY3    $HOME/$SCRIPTS/weather/local_weather.py
0 * * * *               $PY3    $HOME/$SCRIPTS/weather/forecast_collector.py
## HOME AUTOMATION
02 * * * *              $PY3    $HOME/$SCRIPTS/camera/reolink_motion_alerts.py -c re-v2lis -lvl debug
15 * * * *              $PY3    $HOME/$SCRIPTS/camera/reolink_motion_alerts.py -c re-eesuks -lvl debug
0 */2 * * *             $PY3    $HOME/$SCRIPTS/plants/mushroom-grow-toggle.py -lvl debug
## SLACK NOTIFICATION/SIGNALING
20 19 * 10-12,1-3 *     $PY3    $HOME/$SCRIPTS/weather/frost_warning.py -lvl debug # Run Oct-March
17 16 * * 0-5           $PY3    $HOME/$SCRIPTS/weather/daily_weather_and_sig_temp_warn.py -lvl debug
*/10 * * * *            $PY3    $HOME/$SCRIPTS/weather/severe_weather_check.py -lvl debug
17 10 * * *             $PY3    $HOME/$SCRIPTS/weather/moon_phase.py
27 8 * * *              $PY3    $HOME/$SCRIPTS/slackbot/word-of-the-day.py -lvl debug

# Vpulse Automation
#40 03 * * * export DISPLAY=:0; $PY3 $HOME/$SENSORS/vpulse/vpulse_auto.py -lvl debug
