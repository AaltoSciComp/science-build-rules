#!/bin/bash

set -e

PUSH=1
IGNORE_CACHE=''
VERBOSE_BUILD=''
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
  -v|--verbose)
  VERBOSE_BUILD="--progress=plain"
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
  -w|--workers)
  WORKERS=${2//,/ }
  shift
  shift
  ;;
esac
done

if [ -z "$WORKERS" ]; then
  WORKERS="fgci-centos7-slurm-21.08 aalto-ubuntu2004 aalto-ubuntu2204"
  BUILD_SERVERS=y
fi

which docker &> /dev/null || ( echo "'docker'-command was not found. You need to install docker. Quitting!" ; exit 1)
which j2 &> /dev/null || ( echo "'j2'-command was not found. You need to install j2cli. Quitting!" ; exit 1)

cd dockerfiles

if [ ! -z "$BUILD_SERVERS" ]; then
  # Build scibuilder-master and scibuilder-nfs-server
  for TARGET in scibuilder-master scibuilder-nfs-server ; do
    BUILD_RESULT=1
    docker build $VERBOSE_BUILD $IGNORE_CACHE -t $DOCKER_SERVER/$DOCKER_USER/$TARGET:latest -f $TARGET/Dockerfile .
    BUILD_RESULT=$?
    if [ $BUILD_RESULT -eq 0 ]; then
      echo 'Build of "'$TARGET'" was successful.'
    else
      echo 'Build of "'$TARGET'" failed.'
      exit 1
    fi
    if [ $PUSH -eq 0 ]; then
      if [ $BUILD_RESULT -eq 0 ]; then
        docker push $DOCKER_SERVER/$DOCKER_USER/$TARGET:latest
      else
        echo 'Build for "'$TARGET'" failed, will not push.'
      fi
    fi
  done
fi

# Build worker-images
cd scibuilder-worker

for TARGET in $WORKERS ; do

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

  # Build target image
  docker build --build-arg TARGET=$TARGET $VERBOSE_BUILD $IGNORE_CACHE -t $DOCKER_URL -f $TARGET/Dockerfile .
  BUILD_RESULT=$?
  if [ $BUILD_RESULT -eq 0 ]; then
    echo 'Build of "'$TARGET'" was successful.'
  else
    echo 'Build of "'$TARGET'" failed.'
    exit 1
  fi
  if [ $PUSH -eq 0 ]; then
    if [ $BUILD_RESULT -eq 0 ]; then
      docker push $DOCKER_URL
    else
      echo 'Build for "'$TARGET'" failed, will not push.'
    fi
  fi

done
