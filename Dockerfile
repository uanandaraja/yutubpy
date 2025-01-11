FROM python:3.10-slim

WORKDIR /app

RUN apt-get update && \
    apt-get install -y --no-install-recommends ffmpeg && \
    rm -rf /var/lib/apt/lists/*

COPY pyproject.toml main.py ./

RUN curl -o cookies.txt https://storage.nizzy.xyz/cookies.txt && \
    pip install --no-cache-dir .
    
EXPOSE 7000

CMD ["python", "main.py"]
