#!/bin/bash
export PYTHONPATH=$PYTHONPATH:`pwd`

pushd examples/raw > /dev/null
    diff <(python test.py) test.out
    diff <(python -m ipfs_build) test.out
popd > /dev/null
