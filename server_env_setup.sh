#!/usr/bin/env bash

# Create directories
mkdir data keys logs extras

# Install python dependencies
sudo apt-get install git git-core python3-pip python3-dev python3-pandas python3-mysqldb \
    python3-serial libmysqlclient-dev

# Clone kavalkilu to home dir
git clone git@github.com:barretobrock/kavalkilu.git ${HOME}

# To run some of the scripts, bash is recommended over dash.
#   To reconfigure `sh` to point to bash, run this
# TODO Check if dash is default first
sudo dpkg-reconfigure dash

# Store git credentials to avoid prompt
echo "Beginning git credential storage"
git config --global credential.helper store
git pull

# Set environment variables
#echo -e "\nexport KAVPY=/usr/bin/python3\nexport KAVDIR=${HOME}/kavalkilu" >> ~/.bashrc
