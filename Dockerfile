# syntax=docker/dockerfile:1
   
FROM python:3.11-slim

ARG VERSION_TAG
ENV VERSION=$VERSION_TAG

# Copy files for poetry
COPY pyproject.toml /app/pyproject.toml

# Copy source code
COPY bot/ /app/bot

WORKDIR /app

RUN pip3 install poetry
RUN poetry config virtualenvs.create false
RUN poetry install --no-dev --no-root

CMD ["poetry", "run", "python", "-OO", "-m", "bot"]
