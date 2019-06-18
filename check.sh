#!/bin/bash

pylint buildrules
pylint tests
python -m unittest discover
