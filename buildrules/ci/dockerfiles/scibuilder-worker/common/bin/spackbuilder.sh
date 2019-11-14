#!/bin/bash

set -euo pipefail

TARGET=${WORKERNAME#"worker_"}
CONF_DIR=$(pwd)/configs/$TARGET/spack

[[ -f /usr/share/lmod/lmod/init/bash ]] && . /usr/share/lmod/lmod/init/bash

[[ -f /build/spack/build/spack/share/spack/setup-env.sh ]] && . /build/spack/build/spack/share/spack/setup-env.sh

set +u

spack -C $CONF_DIR "$@"

exit $?
