FROM python:3.10-slim

WORKDIR /app

# Install ffmpeg and dependencies
RUN apt-get update && \
    apt-get install -y --no-install-recommends ffmpeg && \
    rm -rf /var/lib/apt/lists/*

COPY pyproject.toml main.py .env ./

RUN pip install --no-cache-dir .

EXPOSE 8080

CMD ["python", "main.py"]
