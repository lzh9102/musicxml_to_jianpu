#!/bin/sh

# unittest
./test_main.py || exit 1

# integration tests
(cd tests && ./run.sh)
