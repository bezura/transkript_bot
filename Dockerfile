FROM python:3.13-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app/src

WORKDIR /app

RUN apt-get update \
    && apt-get install -y --no-install-recommends ffmpeg \
    && rm -rf /var/lib/apt/lists/*

COPY pyproject.toml ./pyproject.toml

RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir \
        aiofiles \
        aiogram \
        aiosqlite \
        faster-whisper \
        psutil \
        pydantic-settings

COPY src ./src

RUN mkdir -p /app/data/media

CMD ["python", "-m", "transkript_bot.main"]
