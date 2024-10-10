FROM python:3.12.7-slim

ENV PYTHONDONTWRITEBYTECODE yes

RUN apt-get update
RUN apt-get install -y git

WORKDIR /app

COPY server.py server.py

