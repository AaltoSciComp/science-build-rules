#!/bin/bash

set -euo pipefail

BUILDBOT_UID=$(id -u buildbot)
if [[ $BUILDBOT_UID != $WORKER_UID ]]; then
  usermod -u $WORKER_UID buildbot
  groupmod -g $WORKER_UID buildbot
  chown -Rh $WORKER_UID:$WORKER_UID /buildbot
fi
echo 'entry.sh:'
echo '    buildbot UID: '$(id -u buildbot)
echo '    worker   UID: '$WORKER_UID

HOME_OWNER=$(stat -c %u /home/buildbot)
if [[ $HOME_OWNER != $WORKER_UID ]]; then
  echo '/home/buildbot is owned by user '$HOME_OWNER
  exit 1
fi

cd /buildbot
exec gosu buildbot "$@"
