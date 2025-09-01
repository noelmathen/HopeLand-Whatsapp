FROM python:3.11-slim

# System deps
RUN apt-get update && apt-get install -y --no-install-recommends \
    ca-certificates tzdata && \
    rm -rf /var/lib/apt/lists/*

# App dirs
WORKDIR /app
RUN mkdir -p /data/logs /secrets

# Copy code
COPY requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r /app/requirements.txt

COPY . /app

# Set timezone env if you want (optional)
ENV PYTHONUNBUFFERED=1

# Default command is gunicorn; overridden in docker-compose for the digest service
CMD ["gunicorn","-w","2","-k","gthread","--threads","8","-b","0.0.0.0:3000","app:app","--timeout","120"]
