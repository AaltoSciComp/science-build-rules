****************
Anaconda-builder
****************

Anaconda-builder uses `Anaconda <https://www.anaconda.com/>`_ for
installing software.

After validating the configuration structure, the build runs the
following build rules:

1. Create folders for modules, software and temprorary files.
2. Download installer file.
3. Checksum the installer file.
4. Install a new conda prefix using the installer.
5. If the installation already exists, use the `environment.yml` created by
   the previous installation to install previously installed packages.
   Set flags that locks these packages for the following installation commands.
6. Install packages using conda.
7. Install packages using pip.
8. Export `environment.yml` from the built environment and log the installed
   environment into `installed_environments.yml`.
6. Recreate modules
