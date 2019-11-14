#!/bin/bash

set -e

PUSH=1
IGNORE_CACHE=''
DOCKER_SERVER=${DOCKER_SERVER:-"docker.io"}
DOCKER_USER=${DOCKER_USER:-"aaltoscienceit"}

for ARG in "$@"
do
case $ARG in
  -p|--push)
  PUSH=0
  shift
  ;;
  -i|--ignore-cache)
  IGNORE_CACHE=--no-cache
  shift
  ;;
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
which j2 &> /dev/null || ( echo "'j2'-command was not found. You need to install j2cli. Quitting!" ; exit 1)

cd dockerfiles

# Build scibuilder-master and scibuilder-nfs-server
for TARGET in scibuilder-master scibuilder-nfs-server ; do
  BUILD_RESULT=1
  docker build $IGNORE_CACHE -t $DOCKER_SERVER/$DOCKER_USER/$TARGET:latest -f $TARGET/Dockerfile .
  BUILD_RESULT=$?
  if [ $BUILD_RESULT -eq 0 ]; then
    echo 'Build of "'$TARGET'" was successful.'
  else
    echo 'Build of "'$TARGET'" failed.'
  fi
  if [ $PUSH -eq 0 ]; then
    if [ $BUILD_RESULT -eq 0 ]; then
      docker push $DOCKER_SERVER/$DOCKER_USER/$TARGET:latest
    else
      echo 'Build for "'$TARGET'" failed, will not push.'
    fi
  fi
done

# Build worker-images
cd scibuilder-worker

for TARGET in fgci-centos7 ; do

  DOCKER_URL=$DOCKER_SERVER/$DOCKER_USER/scibuilder-worker:$TARGET
  BUILD_RESULT=1

  # Create Dockerfile
  cat > $TARGET/Dockerfile << EOF
#
# This file has been automatically created by build-images.sh
#
# Please edit Dockerfile.j2 instead.
#
EOF
  j2 $TARGET/Dockerfile.j2 >> $TARGET/Dockerfile

  # Build base image
  docker build --build-arg TARGET=$TARGET $IGNORE_CACHE -t $DOCKER_URL -f $TARGET/Dockerfile .
  BUILD_RESULT=$?
  if [ $BUILD_RESULT -eq 0 ]; then
    echo 'Build of "'$TARGET'" was successful.'
  else
    echo 'Build of "'$TARGET'" failed.'
  fi
  if [ $PUSH -eq 0 ]; then
    if [ $BUILD_RESULT -eq 0 ]; then
      docker push $DOCKER_URL
    else
      echo 'Build for "'$TARGET'" failed, will not push.'
    fi
  fi

  cd ..
done
