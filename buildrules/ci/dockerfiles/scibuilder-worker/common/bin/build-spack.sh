#!/bin/bash

set -euo pipefail

BUILDER=spack
COMMAND=$1
TARGET=${WORKERNAME#"worker_"}
CONF_DIR=/build/$BUILDER/build/configs/$TARGET/$BUILDER

[[ -f /usr/share/lmod/lmod/init/bash ]] && . /usr/share/lmod/lmod/init/bash

[[ -f /build/spack/build/spack/share/spack/setup-env.sh ]] && . /build/spack/build/spack/share/spack/setup-env.sh

set +u

echo "Running the $BUILDER builder: python3 -u -m buildrules $BUILDER $COMMAND $CONF_DIR"

python3 -u -m buildrules $BUILDER $COMMAND $CONF_DIR

exit $?
