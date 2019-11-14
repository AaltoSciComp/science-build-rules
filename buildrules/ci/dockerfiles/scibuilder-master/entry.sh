#!/bin/bash

set -uo pipefail

BUILDBOT_UID=$(id -u buildbot)
USER_EXISTS=$?

set -eE

if [[ $USER_EXISTS != 0 ]]; then
  groupadd -g $WORKER_UID buildbot
  useradd -m -s /bin/bash -u $WORKER_UID -N -g $WORKER_UID buildbot
  chown -Rh $WORKER_UID:$WORKER_UID /var/lib/buildbot
elif [[ $BUILDBOT_UID != $WORKER_UID ]]; then
  usermod -u $WORKER_UID buildbot
  groupmod -g $WORKER_UID buildbot
  gpasswd -a buildbot docker &> /dev/null
  chown -Rh $WORKER_UID:$WORKER_UID /buildbot
fi

HOME_OWNER=$(stat -c %u /home/buildbot)
if [[ $HOME_OWNER != $WORKER_UID ]]; then
  echo '/home/buildbot is owned by user '$HOME_OWNER
  exit 1
fi

cd /var/lib/buildbot
exec su-exec buildbot "$@"
