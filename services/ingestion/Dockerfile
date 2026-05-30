FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app

RUN python -m venv .venv
COPY requirements.txt .
RUN .venv/bin/pip install --upgrade pip \
    && .venv/bin/pip install -r requirements.txt

COPY . .

EXPOSE 8001

CMD [".venv/bin/python", "manage.py", "runserver", "0.0.0.0:8001"]

