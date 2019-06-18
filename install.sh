#!/bin/bash

set -euo pipefail

CONDA_PREFIX=$(pwd)/conda

if [[ ! -d "$CONDA_PREFIX" ]] ; then
  echo 'No conda found in '$CONDA_PREFIX
  echo 'Downloading Miniconda...'
  wget https://repo.anaconda.com/miniconda/Miniconda3-latest-Linux-x86_64.sh &> /dev/null
  echo 'Installing Miniconda to '$CONDA_PREFIX
  bash Miniconda3-latest-Linux-x86_64.sh -p $(pwd)/conda -b > /dev/null
  rm Miniconda3-latest-Linux-x86_64.sh
fi

export PATH=${CONDA_PREFIX}/bin:$PATH

echo 'Creating environment for buildrules'
conda env create -f environment.yaml > /dev/null

echo 'Finished.'
echo 'You can launch the Python environment with:'
echo 'export PATH=$(pwd)/conda/bin:$PATH && source activate buildrules'
