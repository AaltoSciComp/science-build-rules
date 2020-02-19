#!/bin/bash

set -e

PUSH=1
IGNORE_CACHE=''
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

which docker &> /dev/null || ( echo "'docker'-command was not found. You need to install docker. Quitting!" ; exit 1)

# Pull scibuilder-master and scibuilder-nfs-server
for TARGET in scibuilder-master scibuilder-nfs-server ; do
  PULL_RESULT=1
  docker pull $IGNORE_CACHE $DOCKER_SERVER/$DOCKER_USER/$TARGET:latest
  PULL_RESULT=$?
  if [ $PULL_RESULT -eq 0 ]; then
    echo 'Pull of "'$TARGET'" was successful.'
  else
    echo 'Pull of "'$TARGET'" failed.'
  fi
done

# Pull worker-images

for TARGET in fgci-centos7 aalto-ubuntu1804 ; do

  DOCKER_URL=$DOCKER_SERVER/$DOCKER_USER/scibuilder-worker:$TARGET
  PULL_RESULT=1

  # Pull target image
  docker pull $DOCKER_URL
  PULL_RESULT=$?
  if [ $PULL_RESULT -eq 0 ]; then
    echo 'Build of "'$TARGET'" was successful.'
  else
    echo 'Build of "'$TARGET'" failed.'
  fi
done
