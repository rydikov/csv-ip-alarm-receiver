FROM python:3.12.7-slim

ENV TZ Europe/Moscow
ENV PYTHONDONTWRITEBYTECODE yes

WORKDIR /app

COPY server.py server.py

