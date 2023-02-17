#!/bin/bash

while true
do
    git pull
    poetry update
    poetry install
    $1 -m bot -OO
done
