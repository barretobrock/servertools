#!/usr/bin/env bash

# Set bash instead of dash
# TODO Check if dash is default first
sudo dpkg-reconfigure dash

# Create directories
mkdir data keys logs extras

# Install python dependencies
sudo apt install build-essential git python3-pip python3-dev python3-venv python3-pandas python3-serial chromium-chromedriver


# Clone kavalkilu to home dir
git clone git@github.com:barretobrock/kavalkilu.git ${HOME}


