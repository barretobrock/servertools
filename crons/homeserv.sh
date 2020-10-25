#!/usr/bin/env bash

# VARIABLES
SCRIPTS=extras/servertools/scripts
PY3=/home/bobrock/venvs/stools/bin/python3

# LOG ANALYSIS
#0 */4 * * *            $PY3    $HOME/$SCRIPTS/log_reader.py
#32 3 20 * *            $PY3    $HOME/$SCRIPTS/log_remover.py -lvl debug
## PIHOLE

## MYSQL
#30 6 * * *             $PY3    $HOME/$SCRIPTS/grafana/grafana.py
# SYS DATA COLLECTION
*/2 * * * *             $PY3    $HOME/$SCRIPTS/net/machine-connected.py
0 */3 * * *             $PY3    $HOME/$SCRIPTS/net/speedtest-logger.py
## ENV DATA COLECTION
#*/10 * * * *           $PY3    $HOME/$SCRIPTS/weather/ecobee_temps.py
*/10 * * * *            $PY3    $HOME/$SCRIPTS/weather/local_weather.py
0 * * * *               $PY3    $HOME/$SCRIPTS/weather/forecast_collector.py
## HOME AUTOMATION
*/5 03-22 * * *         $PY3    $HOME/$SCRIPTS/camera/amcrest_notify_zone.py -lvl debug
5 23 * * *              $PY3    $HOME/$SCRIPTS/camera/amcrest_nighttime.py -lvl debug
#02 0-9/3 * * *         $PY3    $HOME/$SCRIPTS/camera/motion_alerts.py -lvl debug
0 */10 * * *            $PY3    $HOME/$SCRIPTS/camera/motion_alerts_30m.py -lvl debug
## SLACK NOTIFICATION/SIGNALING
20 19 * 10-12,1-3 *     $PY3    $HOME/$SCRIPTS/weather/frost_warning.py # Run Oct - March only
17 16 * * 0-5           $PY3    $HOME/$SCRIPTS/weather/daily_weather_and_sig_temp_warn.py
*/10 * * * *            $PY3    $HOME/$SCRIPTS/weather/severe_weather_check.py
17 10 * * *             $PY3    $HOME/$SCRIPTS/weather/moon_phase.py
#15 */4 * * *           $PY3    $HOME/$SCRIPTS/slackbot/slack_logger.py
#21 9 * * *              $PY3    $HOME/$SCRIPTS/slackbot/emoji_scraper.py
#19 10-14 * * 1-5        $PY3    $HOME/$SCRIPTS/slackbot/memeraker.py -lvl debug
27 8 * * *              $PY3    $HOME/$SCRIPTS/slackbot/word-of-the-day.py -lvl debug

# Vpulse Automation
#40 03 * * * export DISPLAY=:0; $PY3 $HOME/$SENSORS/vpulse/vpulse_auto.py -lvl debug
