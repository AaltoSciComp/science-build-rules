#!/bin/bash

set -euo pipefail

COMMAND=$1
TARGET=${WORKERNAME#"worker_"}
CONF_DIR=$(pwd)/configs/$TARGET/singularity

[[ -f /usr/share/lmod/lmod/init/bash ]] && . /usr/share/lmod/lmod/init/bash

set +u

python3 -u -m buildrules singularity $COMMAND $CONF_DIR

exit $?
