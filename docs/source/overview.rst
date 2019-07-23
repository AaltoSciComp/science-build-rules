===============================
Overview of science-build-rules
===============================

``science-build-rules`` is a suite of Python classes and utilities that
make it easier to create automated builds with Spack, Singularity and
Anaconda. It is designed to run with ``science-build-environment``, but it
can also be run independently. The basic structure is described below:

.. image:: ../images/builder_structure.svg
   :width: 800

Typical build will do the following steps:

1. Read and validate configuration. This is done by the
   ``ConfReader``-class.
2. Build the software based on build rules. This is done by subclasses
   of the ``Builder``-class.
3. Test the installed software. This step is not yet implemented.
4. Deploy software from the build system into a target system with a
   desired deployment strategy. This is done by subclasses of the
   ``Deployer``-class.

Idea in "build-rules" is that a series of operations is performed in a specific way, defined by the ``Builder``-class and configuration files. Each subclass of ``Builder`` is tool specific, for example ``SpackBuilder`` creates builds with Spack. The user chooses the subclass of ``Builder`` designed for the tool they wish to use and modifies configuration files to match their needs.

Before doing a build, configuration files are loaded in and
validated. The build and deployment commands, which are based on the configuration files, are then predefined and wrapped in subclasses of the ``Rule``-class. Each subclass of ``Builder`` and ``Deployer`` can have their own configuration yaml-files and corresponding schemas.
