#!/bin/sh

docker cp config.py $(sudo docker compose ps -q bot):/app/config.py
