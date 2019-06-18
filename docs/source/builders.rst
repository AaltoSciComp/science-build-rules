========
Builders
========

******************************
Common features among builders
******************************

All of the builders share some common features.

Configuration file structure
==============================

When working with ``science-build-environment``, all configuration
files should be stored in the following file structure::

  <build rules repo>/configs/<build target>/<builder>/*.yaml

e.g.::
  
  ~/science-build-rules/configs/centos/spack/packages.yaml

All configuration files should be in yaml-format.

..
  Add chapters on individual builders

.. include:: builders/spack.rst
.. include:: builders/singularity.rst
