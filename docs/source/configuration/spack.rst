************
Spack builds
************

build_config.yaml
=================

Overview
********

The main configuration for a spack build is in build_config.yaml.

The file should contain three keys:

    - ``target_architecture``: This dictionary defines the default
      target arcitecture.
    - ``compilers``: This array defines the desired compilers.
    - ``packages``: This array defines desired end products.

target_architecture
*******************

The ``target_architecture``-dictionary should contain the following keys:

    - ``platform``: Platform that spack should target (e.g. ``linux``).
    - ``os``: Operating system that spack should target (e.g. ``centos7``).
    - ``arch``: Architecture that spack should target (e.g. ``westmere``).

A sample configuration might be something like:

.. code-block:: yaml

    target_architecture:
      platform: linux
      os: centos7
      arch: westmere

compilers
*********

The ``compilers``-array consists of individual compilers as dictionaries.
These compilers are evaluated in sequential order from top to bottom.
System compilers that are used to install other compilers should be positioned
at the start of the array.

Each compiler can contain the following keys:

    - ``name``: Name of the compiler in spack (e.g. ``gcc``).
    - ``version``: Version of the compiler in spack (e.g. ``9.2.0``).
    - ``system_compiler``: Boolean value that tells if the compiler
      is a system compiler (Default: false).
    - ``licenses``: Array of license files that need to be copied into
      the installation directory. More information on this at the
      licenses-page (TODO) (e.g. ``[license.lic]``).
    - ``variants``: Additional variants that the installation should use
      (e.g. ``+binutils`` for ``gcc``).
    - ``dependencies``: Additional dependencies for the installation. Compilers
      that are built by system compilers should depend on them.
      Further compilers should also depend on main compiler.
      Otherwise the compilers might try to build themselves again.
      (e.g. ``%gcc@4.8.5`` for ``gcc@9.2.0`` and ``%gcc@9.2.0`` for
      ``intel-parallel-studio``).
    - ``extra_flags``: Array of extra flags that should be given to ``spack
      install``-command (e.g. ``--jobs 4`` to limit the build to four cpus).
    - ``flags``: Dictionary of flag-parameters that should be written to
      ``~/.spack/linux/compilers.yaml``. These flags are then added to every
      build done with these compilers. Possible keys are ``cflags``, ``cxxflags``,
      ``cppflags``, ``fflags``, ``ldflags``, ``ldlibs`` (e.g. ``{ 'cflags': '-g' , 
      'cxxflags': '-g' }`` would compile all C and C++ codes with debug flags).
      Architecture flags are added automatically by ``target_architecture``.
    - ``target_architecture``: Target architecture for building this compiler.
      This is important if the system compiler cannot compile software to the
      desired default architecture. Do note that this does not change the
      target for software built with this compiler. It only changes the target
      for compiling this compiler. Structure is the same as for
      ``target_architecture``.

Only ``name`` and ``version`` are required, but in practice one usually needs to
use most of the parameters. An example configuration might look something like
this:

.. code-block:: yaml

    compilers:
      - name: gcc
        version: 4.8.5
        system_compiler: true
        flags:
          cflags: -O2 -g
          cxxflags: -O2 -g
          fflags: -O2 -g
      - name: 'gcc'
        version: 9.2.0
        variants:
          - +piclibs
        dependencies:
          - %gcc@4.8.5
        flags:
          cflags: -O2 -g -ftree-vectorize
          cxxflags: -O2 -g -ftree-vectorize
          fflags: -O2 -g -ftree-vectorize
        target_architecture:
          platform: linux
          os: centos7
          arch: x86_64
      - name: intel-parallel-studio
        version: cluster.2019.3
        licenses:
          - license.lic
        dependencies:
          - %gcc@9.2.0
        flags:
          cflags: -O2 -g
          cxxflags: -O2 -g
          fflags: -O2 -g
        target_architecture:
          platform: linux
          os: centos7
          arch: x86_64

packages
********

The ``packages``-array consists of individual packages as dictionaries.
These packages are evaluated in sequential order from top to bottom.

Each package can contain the following keys:

    - ``name``: Name of the package in spack (e.g. ``gcc``).
    - ``version``: Version of the package in spack (e.g. ``9.2.0``).
    - ``licenses``: Array of license files that need to be copied into
      the installation directory. More information on this at the
      licenses-page (TODO) (e.g. ``[license.lic]``).
    - ``variants``: Additional variants that the installation should use
      (e.g. ``fabrics=verbs`` for ``openmpi``).
    - ``dependencies``: Additional dependencies for the installation.
      (e.g. ``%gcc@9.2.0`` or ``^python@3:``).
    - ``extra_flags``: Array of extra flags that should be given to ``spack
      install``-command (e.g. ``--jobs 4`` to limit the build to four cpus).
    - ``target_architecture``: Target architecture for building this package.
      Structure is the same as for ``target_architecture``.

Only ``name`` and ``version`` are required. Default variants and versions
should be set in ``packages.yaml``. An example configuration might look
something like this:

.. code-block:: yaml

    packages:
      - name: 'openmpi'
        version: 3.1.4
      - name: 'python'
        version: 3.7.4
      - name: 'r'
        version: 3.6.1
      - name: 'py-gpaw'
        version: 1.3.0
        variants:
          - '+fftw'
          - '+mpi'
          - '+scalapack'
