#!/bin/bash

set -euo pipefail

COMMAND=$1
TARGET=${WORKERNAME#"worker_"}
CONF_DIR=$(pwd)/configs/$TARGET/spack

[[ -f /usr/share/lmod/lmod/init/bash ]] && . /usr/share/lmod/lmod/init/bash

[[ -f /build/spack/build/spack/share/spack/setup-env.sh ]] && . /build/spack/build/spack/share/spack/setup-env.sh

set +u

python3 -u -m buildrules spack $COMMAND $CONF_DIR

exit $?
