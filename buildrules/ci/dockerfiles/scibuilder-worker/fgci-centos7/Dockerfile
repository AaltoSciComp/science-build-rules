#
# This file has been automatically created by build-images.sh
#
# Please edit Dockerfile.j2 instead.
#
FROM centos:centos7

RUN yum install -y epel-release           \
  && yum update -y                        \
  && yum clean all

RUN yum groups mark install "Development Tools" \
  && yum groups mark convert "Development Tools" \
  && yum groupinstall -y "Development Tools" \
  && yum clean all

# Base dependencies
RUN yum update -y && yum install -y       \
  Lmod                                    \
  bash-completion                         \
  cmake                                   \
  curl                                    \
  git                                     \
  libarchive-devel                        \
  libnl3                                  \
  libnl3-devel                            \
  libuuid-devel                           \
  openssh                                 \
  openssl-devel                           \
  python                                  \
  python-devel                            \
  python-jinja2                           \
  python-pip                              \
  python-yaml                             \
  python36                                \
  python36-coloredlogs                    \
  python36-devel                          \
  python36-jinja2                         \
  python36-jsonschema                     \
  python36-pip                            \
  python36-requests                       \
  python36-sh                             \
  python36-yaml                           \
  rsync                                   \
  shadow-utils                            \
  squashfs-tools                          \
  sudo                                    \
  tcl                                     \
  unzip                                   \
  wget                                    \
  which                                   \
  && yum clean all

# Install singularity

RUN yum update -y && yum install -y       \
  singularity                             \
  && yum clean all

# Add Open HPC slurm

ARG TARGET

RUN yum install -y https://github.com/openhpc/ohpc/releases/download/v1.3.GA/ohpc-release-1.3-1.el7.x86_64.rpm

RUN yum update -y && yum install -y       \
  pmix                                    \
  pmix-devel                              \
  libibverbs                              \
  libibverbs-devel                        \
  ohpc-slurm-client                       \
  slurm-devel-ohpc                        \
  slurm-libpmi-ohpc                       \
  && yum clean all

# Add other packages

RUN yum update -y && yum install -y       \
  mesa-dri-drivers                        \
  && yum clean all

RUN echo 'buildbot ALL=(ALL) NOPASSWD:SETENV: /usr/local/bin/singularity, /bin/chown' >> /etc/sudoers

# Install gosu
RUN set -eux; \
    gpg --keyserver pool.sks-keyservers.net --recv-keys B42F6819007F00F88E364FD4036A9C25BF357DD4 \
    && curl -o /usr/local/bin/gosu -SL "https://github.com/tianon/gosu/releases/download/1.2/gosu-amd64" \
    && curl -o /usr/local/bin/gosu.asc -SL "https://github.com/tianon/gosu/releases/download/1.2/gosu-amd64.asc" \
    && gpg --verify /usr/local/bin/gosu.asc \
    && rm /usr/local/bin/gosu.asc \
    && rm -r /root/.gnupg/ \
    && chmod +x /usr/local/bin/gosu \
	  && gosu nobody true

# Install dumb-init
RUN wget -O /usr/local/bin/dumb-init https://github.com/Yelp/dumb-init/releases/download/v1.2.1/dumb-init_1.2.1_amd64 && \
echo "057ecd4ac1d3c3be31f82fc0848bf77b1326a975b4f8423fe31607205a0fe945  /usr/local/bin/dumb-init" | sha256sum -c - && \
chmod 755 /usr/local/bin/dumb-init

# Install more requirements
RUN pip3 --no-cache-dir install twisted[tls] && \
  mkdir /buildbot && \
  useradd -ms /bin/bash buildbot

# Setting buildbot version
ARG BUILDBOT_VERSION=v2.4.0

# Clone buildbot repo
RUN git clone https://github.com/buildbot/buildbot.git /usr/src/buildbot && \
  cd /usr/src/buildbot/worker && \
  git checkout $BUILDBOT_VERSION && \
  cp docker/buildbot.tac /buildbot/buildbot.tac

# Install buildbot
RUN pip3 install /usr/src/buildbot/worker && \
  chown -Rh buildbot.buildbot /buildbot

# Copy builder scripts

COPY ./common/bin/build-singularity.sh /usr/local/bin/build-singularity
RUN  chmod +x /usr/local/bin/build-singularity

COPY ./common/bin/build-spack.sh /usr/local/bin/build-spack
RUN  chmod +x /usr/local/bin/build-spack

COPY ./common/bin/spackbuilder.sh /usr/local/bin/spackbuilder
RUN  chmod +x /usr/local/bin/spackbuilder

COPY ./common/entry.sh /usr/local/bin/entry.sh
RUN  chmod +x /usr/local/bin/entry.sh

ENTRYPOINT ["/usr/local/bin/entry.sh"]
WORKDIR /buildbot
CMD ["/usr/local/bin/dumb-init", "twistd", "-ny", "buildbot.tac"]

USER root

