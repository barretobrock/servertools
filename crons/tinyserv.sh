#!/usr/bin/env bash

# VARIABLES
SCRIPTS=extras/servertools/scripts
PY3=/home/bobrock/venvs/stools/bin/python3

## PIHOLE
#7 * * * *               $PY3    $HOME/$SCRIPTS/piholeinflux/piholeinflux.py -lvl debug
## DATA COLLECTION
## Network
*/2 * * * *             $PY3    $HOME/$SCRIPTS/net/machine-connected.py -lvl debug
#0 */3 * * *             $PY3    $HOME/$SCRIPTS/net/speedtest-logger.py -lvl debug
## Climate
#0 * * * *               $PY3    $HOME/$SCRIPTS/weather/local_weather.py -lvl debug
#0 * * * *               $PY3    $HOME/$SCRIPTS/weather/forecast_collector.py -lvl debug
#*/10 * * * *            $PY3    $HOME/$SCRIPTS/weather/ha_temp_recorder.py -lvl debug

## HOME AUTOMATION
### Camera
#02 * * * *              $PY3    $HOME/$SCRIPTS/camera/reolink_motion_alerts.py -c re-v2lis -lvl debug
#15 * * * *              $PY3    $HOME/$SCRIPTS/camera/reolink_motion_alerts.py -c re-eesuks -lvl debug
#*/5 * * * *             $PY3    $HOME/$SCRIPTS/camera/timelapse.py -c ac-allr6du -lvl debug
#*/5 * * * *             $PY3    $HOME/$SCRIPTS/camera/timelapse.py -c ac-yler6du -lvl debug
#*/5 * * * *             $PY3    $HOME/$SCRIPTS/camera/timelapse.py -c re-v2lis -lvl debug
30 6 * * * *            $PY3    $HOME/$SCRIPTS/camera/timelapse_poster.py
### Other
#0 * * * *            $PY3    $HOME/$SCRIPTS/plants/mushroom-grow-toggle.py -lvl debug  # Run at the top of every hour

## SLACK NOTIFICATION/SIGNALING
20 19 * 10-12,1-3 *     $PY3    $HOME/$SCRIPTS/weather/frost_warning.py -lvl debug # Run Oct-March
#17 16 * * 0-5           $PY3    $HOME/$SCRIPTS/weather/daily_weather_and_sig_temp_warn.py -lvl debug
#*/10 * * * *            $PY3    $HOME/$SCRIPTS/weather/severe_weather_check.py -lvl debug
17 10 * * *             $PY3    $HOME/$SCRIPTS/weather/moon_phase.py
#27 9 * * *              $PY3    $HOME/$SCRIPTS/slackbot/emoji_scraper.py -lvl debug
#27 8 * * *              $PY3    $HOME/$SCRIPTS/slackbot/word-of-the-day.py -lvl debug
#0 9 * * 1-5             $PY3    $HOME/$SCRIPTS/finance/stonks-ticker.py -lvl debug

## SELENIUM
### Apt price scraping
#05 05 * * * export DISPLAY=:0; $PY3 $HOME/$SCRIPTS/net/apt_prices.py -lvl debug
### Vpulse Automation
#40 03 * * * export DISPLAY=:0; $PY3 $HOME/$SENSORS/vpulse/vpulse_auto.py -lvl debug
