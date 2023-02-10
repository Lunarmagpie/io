# syntax=docker/dockerfile:1
   
FROM python:3.11-slim-buster

COPY config.py config.py
COPY . /app

WORKDIR /app

RUN pip3 install poetry
RUN poetry config virtualenvs.create false
RUN poetry install --no-dev --no-root

WORKDIR /app
CMD ["poetry", "run", "python", "-m", "bot", "-OO"]
