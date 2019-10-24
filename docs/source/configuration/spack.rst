************
Spack builds
************

build_config.yaml
=================

Overview
********

The main configuration for a spack build is in build_config.yaml.

The file should contain three keys:

    - `target_architecture`: This dictionary defines the default
      target arcitecture.
    - `compilers`: This array defines the desired compilers.
    - `packages`: This array defines desired end products.

target_architecture
*******************

The `target_architecture` should contain the following keys:

    - `platform`: Platform that spack should target (e.g. `linux`)
    - `os`: Operating system that spack should target (e.g. `centos7`)
    - `arch`: Architecture that spack should target (e.g. `westmere`)

A sample configuration might be something like::

    target_architecture:
      platform: linux
      os: centos7
      arch: westmere
