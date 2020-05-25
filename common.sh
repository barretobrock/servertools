#!/usr/bin/env bash
# ------------------------------------------
# COMMON VARIABLES / FUNCTIONS
# ------------------------------------------
BLUE="\e[34m"
GREEN="\e[32m"
RED="\e[31m"
RESET="\e[0m"

contains () {
    # Checks if the variable ($2) is in the space-separated list provided ($1)
    LIST=$1
    VAR=$2
    [[ "${LIST}" =~ (^|[[:space:]])"${VAR}"($|[[:space:]]) ]];
}

announce_section () {
    # Makes sections easier to see in output
    SECTION_BRK="\n==============================\n"
    SECTION="${1}"
    printf "${BLUE}${SECTION_BRK}${SECTION}${SECTION_BRK}${RESET}"
}

function parse_yaml {
   local prefix=$2
   local s='[[:space:]]*' w='[a-zA-Z0-9_]*' fs=$(echo @|tr @ '\034')
   sed -ne "s|^\($s\):|\1|" \
        -e "s|^\($s\)\($w\)$s:$s[\"']\(.*\)[\"']$s\$|\1$fs\2$fs\3|p" \
        -e "s|^\($s\)\($w\)$s:$s\(.*\)$s\$|\1$fs\2$fs\3|p"  $1 |
   awk -F${fs} '{
      indent = length($1)/2;
      vname[indent] = $2;
      for (i in vname) {if (i > indent) {delete vname[i]}}
      if (length($3) > 0) {
         vn=""; for (i=0; i<indent; i++) {vn=(vn)(vname[i])("_")}
         printf("%s%s%s=\"%s\"\n", "'${prefix}'",vn, $2, $3);
      }
   }'
}

arg_parse() {
    # Parses arguments from command line
    POSITIONAL=()
    while [[ $# -gt 0 ]]
    do
        key="$1"
        case ${key} in
            -s|--skip-deps)
                SKIP_DEPS=1
                shift # past argument
                ;;
            -v|--version)   # Print script name & version
                echo "${NAME} ${VERSION}"
                exit 0
                ;;
            -l|--level)
                LEVEL=${2:-patch}
                shift # past argument
                shift # past value
                ;;
            *)    # unknown option
                POSITIONAL+=("$1") # save it in an array for later
                shift # past argument
                ;;
    esac
    done
    set -- "${POSITIONAL[@]}" # restore positional parameters
    # Check for unknown arguments passed in
    [[ ! -z "${POSITIONAL}" ]] && echo "Unknown args passed: ${POSITIONAL[@]}"
}

# Collect arguments when this is called
arg_parse "$@"
