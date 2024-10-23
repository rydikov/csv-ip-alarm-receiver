FROM python:3.12.7-slim

ENV TZ Europe/Moscow
ENV PYTHONDONTWRITEBYTECODE yes

WORKDIR /app

COPY requires.txt requires.txt
RUN python3 -m pip install --upgrade pip
RUN pip install -r requires.txt

COPY server.py server.py

