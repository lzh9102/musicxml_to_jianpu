#!/bin/sh

# unittest
./test_main.py

# integration tests
(cd tests && ./run.sh)
