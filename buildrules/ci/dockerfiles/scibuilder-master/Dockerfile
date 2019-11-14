FROM buildbot/buildbot-master:v2.4.0

ARG DEBIAN_FRONTEND=noninteractive

USER root

#RUN apk add --upgrade apk-tools --update-cache --repository http://nl.alpinelinux.org/alpine/edge/main/ --allow-untrusted

RUN echo @edgecommunity http://nl.alpinelinux.org/alpine/edge/community >> /etc/apk/repositories && \
    echo @testing http://nl.alpinelinux.org/alpine/edge/testing >> /etc/apk/repositories && \
    apk add --no-cache \
    openssh-client \
    shadow \ 
    bash \
    su-exec

RUN apk update \
    apk upgrade

# Install prometheus plugin

RUN pip install buildbot_prometheus

# Install txrequests for github API

RUN pip install txrequests

COPY ./scibuilder-master/entry.sh /usr/local/bin/entry.sh
RUN  chmod +x /usr/local/bin/entry.sh

ENTRYPOINT ["/usr/local/bin/entry.sh"]
WORKDIR /var/lib/buildbot
CMD ["dumb-init", "/usr/src/buildbot/docker/start_buildbot.sh"]

USER root
