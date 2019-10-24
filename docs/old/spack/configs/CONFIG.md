# SpackAaltoCI configuration

All configuration is organized based on targets. So if build target is centos,
it has its configuration stored in a folder called centos. An image with the
same tag should be present in 
[spack-builder-images](https://hub.docker.com/r/aaltoscienceit/spack-builder-images).

## Package configuration

The desired packages are specified in **pkgconfig.yaml**. Each package has the
following structure:

```yaml
- name: 'paraview'
  parallel: 1
  reinstall: 'dependents'
  compiler: False
  versions:
    - 5.4.1:
      - "+mpi"
      - "+osmesa"
      - "+plugins"
      - "%gcc@5.5.0"
      - "^openmpi"
```

- `name` specifies the name of the spack package. 
- `parallel` is an **optional** key that can be used to specify how many cores 
  you want to use for the build. By default Spack will use all cores. 
- `reinstall` is an another **optional** key that can be used to force 
  uninstallation of the package before reinstallation. It can be `True`, 
  `dependents` or `False`. By setting `dependents` Spack will try to uninstall 
  any packages that depend on said package. Default is `False`.
- `compiler` is an another **optional** key that specifies whether the software
  in question is in fact a compiler that should be made visible to Spack. This
  must be set if you intend to use said software to build additional software.
  Default is `False`.
- `versions` is a list of different versions of said software. Each list element 
  contains a dictionary with key (2.1.2 in the example) that is the program's 
  version number. Its item is a list of strings that specify the spec of said 
  package.

  In general the specs are witten with:
  - `@` designates a specific version of software (`gcc@5.5.0` in the example)
  - `^` indicates a dependency (`^openmpi` in the example)
  - `+` indicates that this configuration option should be included
  - `-` indicates that this configuration option should not be included
  - `a=b` indicates that this configuration option `a` should take the value of `b`


The configuration in question would run
```sh
spack uninstall --force --dependents -y paraview@5.4.1 +mpi +osmesa +plugins %gcc@5.5.0 ^openmpi
spack install -v -j 1paraview@5.4.1 +mpi +osmesa +plugins %gcc@5.5.0 ^openmpi
```
to install the software. The resulting software is a paraview installation that
uses mpi,osmesa and has all the plugins. It uses openmpi to satisfy mpi
dependency and it is built using gcc version 5.5.0. See 
[Spack documention on specs](https://spack.readthedocs.io/en/latest/basic_usage.html#sec-specs)
on more information about specs. 

**It is important** to note that the installation script does the installation
*in order from top to bottom*. This means that compilers, libraries etc. that
are required by higher level software should be defined before their dependents.

## Spack configuration

The system uses three internal configuration files of Spack (see 
[their docs](https://spack.readthedocs.io/en/latest/configuration.html) for
more information):

1. **config.yaml** - Main configuration where installation prefix, module prefix
etc. are defined
2. **packages.yaml** - Configuration file that sets the default packages to use.
3. **modules.yaml** - Configuration file that sets which modules to build and 
what to show there.

The main parts of each configuration are documented in their respective
sections.

### config.yaml

The only parts one needs to change here are the `install_tree`-and 
`module_roots.lmod`-sections. 

Install tree specifies the directory where the software is installed. This 
should be of the form `<sw target folder>/spack/software`. 

`module_roots` has three subcategories: `tcl`,`lmod` and `dotkit`. Currently
these folders should be under `<sw target folder>`. Good settings might be
`tcl: <sw target folder>/spack/tcl`, `dotkit: <sw target folder>/spack/dotkit`
and `lmod: <sw target folder>/spack/modules`.

You should make sure that the resulting **folders are empty** and owned by the 
building user (triton-ci). It is a good idea to create them beforehand to
target system.

### packages.yaml

**packages.yaml** determines the dependency structure of spack installations. If a
spack package requires e.g. MPI, the dependency can be satisfied by various
flavours of OpenMPI,MPICH etc.. In order to get a concise toolchain where
everything depends on some already installed package, one needs to specify the 
versions of software that satisfies these dependencies.

The following documention sets the default version of openmpi to be one
installed with:

```sh
spack install openmpi@2.1.2 %gcc@5.5.0 fabrics=verbs,pmi +thread_multiple
```

```yaml
packages:
  openmpi:
    version: [2.1.2]
    compiler: [gcc@5.5.0]
    variants: fabrics=verbs,pmi +thread_multiple
  gcc:
    version: [5.5.0,5.4.0]
  all:
    compiler: [gcc, intel, pgi, clang, xl, nag]
    providers:
      awk: [gawk]
      blas: [openblas]
      daal: [intel-daal]
      elf: [elfutils]
      gl: [mesa, opengl]
      golang: [gcc]
      ipp: [intel-ipp]
      java: [jdk]
      lapack: [openblas]
      mkl: [intel-mkl]
      mpe: [mpe2]
      mpi: [openmpi, mpich]
      opencl: [pocl]
      openfoam: [openfoam-com, openfoam-org, foam-extend]
      pil: [py-pillow]
      pkgconfig: [pkgconf, pkg-config]
      scalapack: [netlib-scalapack]
      szip: [libszip, libaec]
      tbb: [intel-tbb]
      jpeg: [libjpeg-turbo, libjpeg]
```

The default version of gcc is also set to 5.5.0. If this is not found the next
version (here 5.4.0) is chosen. Specifying these dependencies one can create a
toolchain where each new package depends on some already installed base package.

### modules.yaml

The main things to modify here are under `modules.lmod`. `whitelist` specifies
which modules are always visible. `blacklist` specifies which modules are not
created. Any build dependencies that are not needed during runtime can be added
to this list. If you install higher level software it might be a good idea to 
check after installation what dependencies the resulting module has. Do not
blacklist those dependencies or the module cannot be loaded.

`modules.lmod.all` has `environment` setting that can be used to specify
arbitrary environment variables. `suffixes` can be used to specify suffixes
that are appended to module names. This is important when building variants of
same software. If you have not specified any suffixes that differentiate these
variant, there will be a module name clash. The hierarchical module fix to Lmod
and the name clashes are described in more detail in 
[scripts documentation](../scripts/SCRIPTS.md).

## Deployment configuration

Deployment configuration is done in **deployconfig.yaml**. It has information
on how to deploy the software. Configuration looks like this:
```yaml
config:
  method: 'rsync'
  delete: True
  target_host: 'triton.aalto.fi'
  sources:
    - 'install_tree'
    - 'lmod'
```

Currently `rsync` is the only supported configuration method. `delete`
specifies whether `--delete` should be included in the rsync flags. 
`target_host` is self-evident. `sources` contains a list of folders to copy.
These folders are specified in **config.yaml**. Currently only `install_tree`
and `lmod` are supported.
