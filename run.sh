#!/bin/bash

while true
do
    git pull
    docker compose build
    docker compose up
done
