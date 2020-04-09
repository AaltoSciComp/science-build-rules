#!/bin/bash

set -euo pipefail

BUILDER=anaconda
COMMAND=$1
TARGET=${WORKERNAME#"worker_"}
CONF_DIR=/build/$BUILDER/build/configs/$TARGET/$BUILDER

[[ -f /usr/share/lmod/lmod/init/bash ]] && . /usr/share/lmod/lmod/init/bash

set +u

echo "Running the $BUILDER builder: python3 -u -m buildrules $BUILDER $COMMAND $CONF_DIR"

python3 -u -m buildrules $BUILDER $COMMAND $CONF_DIR

exit $?
