#!/bin/bash
#
# This script sets up a science-build-rules and optionally
# a science-build-environment to user defined location.
#
# This script should not be used for setting up production
# environments, it is meant for testing out the features
# of the build system.
#
# Copyright
# Simo Tuomisto, Aalto University, 2019
#

set -e

print_help() {
  cat << EOF

Usage:

bash $0 -p PREFIX

Flags:

  -e,--science-build-environment
     Installs science-build-environment as well.
     Do note that the nfs server that the environment
     launches might fail if run on a nfs
     mount with root_squash enabled.
  -h,--help
     Print this message.
  -p PREFIX,--prefix PREFIX
     Installation prefix for science-build-rules.
     Default: science-build-rules in current folder.

EOF
}

PREFIX=''
BUILDENV=1
for ARG in "$@"
do
case $ARG in
  -e|--science-build-environment)
  BUILDENV=0
  shift
  ;;
  -h|--help)
  print_help
  exit 0
  shift
  ;;
  -p|--prefix)
  PREFIX=$2
  shift
  shift
  ;;
esac
done

if [ ! "$PREFIX" ]; then
  print_help
  exit 1
fi

PREFIX=$(readlink -f $PREFIX)

if [ -e $PREFIX ]; then
  cat << EOF

Installation prefix '$PREFIX' exits. Stopping.'

EOF
  exit 1
fi

cat << EOF

Starting installation:

-------------------------------------------------------------------------------

EOF

echo -e 'Cloning science-build-rules to "'$PREFIX'"...\n'
git clone --recurse-submodules https://github.com/AaltoScienceIT/science-build-rules.git $PREFIX &> /dev/null
cd $PREFIX

echo -e 'Installing miniconda environment...\n'
./install.sh &> /dev/null

export PATH=${PREFIX}/conda/bin:$PATH
source activate buildrules

echo -e 'Building documentation...\n'
cd docs
make html &> /dev/null

if [ "$BUILDENV" -eq 0 ]; then
  echo -e 'Creating ci configuration to "'${PREFIX}'/configs/ci"...\n'
  cd ${PREFIX}
  cp -r configs/example/ci configs/ci
  sed -i 's/builder uid here/'$(id -u)'/g' configs/ci/build_config.yaml
  sed -i 's:/tmp/science-build-environment:'${PREFIX}'/science-build-environment:g' configs/ci/build_config.yaml
  echo -e 'Running "python -m buildrules ci build configs/ci" to create the CI env..\n'
  python -m buildrules ci build configs/ci &> /dev/null

  echo -e 'Building documentation...\n'
  cd science-build-environment/docs
  make html &> /dev/null
fi

cat << EOF

Done.

-------------------------------------------------------------------------------

Use the following commands to activate the buildrules-environment:

"""
cd ${PREFIX}
export PATH=${PREFIX}/conda/bin:\$PATH
source activate buildrules
source ${PREFIX}/spack/share/spack/setup-env.sh
"""

After activating the environment, you can run the following command
to run the sample installation:

"""
python -m buildrules spack build configs/example/spack
"""

Copy the example to e.g. configs/mytest with:

"""
cp -r configs/example/spack configs/mytest
"""

and try editing build_config.yaml.

Documentation is available in
file://$PREFIX/docs/_build/html/index.html
EOF

if [ "$BUILDENV" -eq 0 ]; then
  cat << EOF

-------------------------------------------------------------------------------

Use the following commands to launch the science-build-environment:

"""
cd ${PREFIX}/science-build-environment
sudo modprobe nfsd
docker-compose up
docker-compose up
"""

After the builder starts, one can login to https://localhost. The example
server uses self signed certificates, so one usually needs to allow for the
connection. After this one can launch an example centos build by clicking
Builders -> Spack - centos -> SpackForce_centos.

Documentation is available in
file://$PREFIX/science-build-environment/docs/_build/html/index.html
EOF
fi
