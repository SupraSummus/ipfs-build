#!/bin/bash

export PYTHONPATH=$PYTHONPATH:`pwd`

for DIR in `find test -mindepth 1 -maxdepth 1`; do
    pushd $DIR > /dev/null
        diff <(python test.py) test.out
        diff <(python -m ipfs_build) test.out
    popd > /dev/null
done
