#!/bin/bash

set -e

DOCKER_SERVER=${DOCKER_SERVER:-"docker.io"}
DOCKER_USER=${DOCKER_USER:-"aaltoscienceit"}

for ARG in "$@"
do
case $ARG in
  -U|--user)
  DOCKER_USER=$2
  shift
  shift
  ;;
  -s|--server)
  DOCKER_SERVER=$2
  shift
  shift
  ;;
esac
done

if [[ "$#" -lt 1 ]]; then
    cat << EOF

    usage: ./$(basename $0) [-s|--server SERVER] [-U|--user user] TARGET [CMD]...

         TARGET              worker target
         CMD                 Run these commands instead of an interactive bash
         -s|--server SERVER  Docker registry for the image
         -U|--user USER      User in Docker registry

EOF
    exit
fi

TARGET=$1

echo 'Creating buildbot home to /tmp/buildbot/'$TARGET
BUILDBOT_HOME=/tmp/buildbot/$TARGET
mkdir -p ${BUILDBOT_HOME}

CMDS=""
FLAGS="-it"
if [[ "$#" -gt 1 ]]; then
    CMDS='-c "'${@:2}'"'
    echo $CMDS
    FLAGS=""
fi
DOCKER_CMD="docker $FLAGS run --privileged --rm -e WORKER_UID=$(id -u) -e HOME=/home/buildbot -v ${BUILDBOT_HOME}:/home/buildbot:rw aaltoscienceit/scibuilder-worker:$TARGET bash -l $CMDS"
cat << EOF

Running worker with command:

  ${DOCKER_CMD}

EOF

eval ${DOCKER_CMD}
