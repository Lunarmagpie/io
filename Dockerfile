# syntax=docker/dockerfile:1
   
FROM python:3.11-slim

COPY . /app

WORKDIR /app

RUN apt-get update
RUN apt-get install git -y

RUN chmod +x run.sh
RUN pip3 install poetry
RUN poetry config virtualenvs.create false
RUN poetry install --no-dev --no-root

CMD ["./run.sh", "python3"]
