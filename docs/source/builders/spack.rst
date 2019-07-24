*************
Spack-builder
*************

Spack-builder uses `Spack <https://spack.io>`_ for installing software.
Before running the builder `spack` should be available in the shell that
launches the build.

After validating the configuration structure, the build runs the
following build rules:

1. Reindex installed packages
2. Remove old compilers configuration file
3. Add existing compilers
4. Install compilers
5. Install packages
6. Recreate modules
