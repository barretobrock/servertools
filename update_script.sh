#!/usr/bin/env bash
#/      --update_script.sh--
#/  Pulls changes from remote master and then updates the local python package
#/
#/  Usage: update_script.sh [options]
#/
#/  Options
#/      -s|--skip-deps                      Skips update of dependencies.
#/      -v|--version                        Prints script name & version.
#/

# DEFAULT VARIABLES
# ------------------------------------------
NAME="Repo Update Script"
VERSION="0.0.2"
SKIP_DEPS=0

# Import common variables / functions
source ./common.sh
eval $(parse_yaml project.yaml)

echo "${REPO_DIR}"

#NODEPS_FLAG=''
#if [[ "${SKIP_DEPS}" == "1" ]];
#then
#    echo "Not installing dependencies"
#    NODEPS_FLAG="--no-deps"
#fi
#
## GIT PULL
## ------------------------------------------
#announce_section "Pulling update from git repo"
#(cd ${REPO_DIR} && git pull origin master)
#
## PY PACKAGE UPDATE
## ------------------------------------------
## Then update the python package locally
#announce_section "Beginning update of ${REPO}"
#python3 -m pip install ${GIT_URL} --upgrade ${NODEPS_FLAG}
#
#announce_section "Process completed"
