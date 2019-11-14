# science-build-rules

science-build-rules is a framework for doing consistent builds of
scientific software and deploying them to target systems. It consists
of `buildrules`-package that constains Builders for:

1. [Spack](https://spack.io)
2. [Singularity](https://sylabs.io/singularity) (work-in-progress)
3. [Anaconda](https://anaconda.org) (work-in-progress)

After builds the software is deployed using a Deployer. Currently there's
only one Deployer: `RsyncDeployer`.

## Quick installation

![](docs/images/install.gif)

Quick installation can be done by running the following commands:

```sh
git clone --recurse-submodules https://github.com/AaltoScienceIT/science-build-rules.git
cd science-build-rules
./install.sh
```

This does the following things:

1. Clones both the science-build-rules repo and the latest spack upstream repo.
2. Installs miniconda to science-build-rules/conda
3. Installs an environment called `buildrules` to the conda environment.

If you have your own `anaconda` setup you can run
```sh
conda env create -f environment.yaml
```

to create the environment.

Activating the environment:
```
export PATH=$(pwd)/conda/bin:$PATH
source activate buildrules
source spack/share/spack/setup-env.sh
```

## Creating documentation

All of the documentation is done by `sphinx`. 

After installation:

```sh
cd docs
make html
```

Documentation can be found in `docs/_build/html/index.html`

## Running test build

After installation, you can find out what a test build does with:

```sh
python -m buildrules spack describe configs/example/spack
```

To do the build, you can run:

```sh
python -m buildrules spack build configs/example/spack
```
