FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app.py .
COPY custom.css .

EXPOSE 8080

RUN useradd -m app_user
USER app_user

CMD ["marimo", "run", "app.py", "--host", "0.0.0.0", "-p", "8080", "--no-token"]
