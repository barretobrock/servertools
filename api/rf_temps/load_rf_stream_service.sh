#!/usr/bin/env bash
# LOADS SERVICE INTO SYSTEMD

SERVICEFILE=rf_stream.service
SRC_FPATH=~/extras/servertools/scripts/rf_temps/${SERVICEFILE}
LIB_FPATH=/lib/systemd/system/${SERVICEFILE}

# Copy the service file to lib
sudo cp ${SRC_FPATH} ${LIB_FPATH}
# Set permissions on it - owner has r/w perms, everyone else has read-only
sudo chmod 644 ${LIB_FPATH}
# Load service & allow boot on restart
sudo systemctl daemon-reload
sudo systemctl enable ${LIB_FPATH}
