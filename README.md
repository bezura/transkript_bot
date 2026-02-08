# Transkript Bot (aiogram v3)

Бот для транскрибации аудио/видео в Telegram с очередью, прогрессом и разделением по говорящим (если доступна diarization).

## Возможности
- ЛС, группы и супергруппы (включая топики).
- Доступ только по allowlist, админы чатов авто‑разрешены в своих чатах.
- Очередь задач с номером и ETA.
- Прогресс по стадиям (скачивание → конвертация → распознавание → отправка).
- Результат в 3 форматах: TXT, MD, JSON.
- Авто‑shutdown после простоя (по умолчанию 5 минут).
- Админ‑панель (root‑admin) со статистикой и системной информацией.

## Требования
- Python 3.13+
- `ffmpeg` в системе
- Для больших файлов: локальный Bot API server (официальный) и переменная `BOT_API_BASE_URL`
- Для GPU/WhisperX: установлен `whisperx` CLI и доступен `nvidia-smi` (опционально)
- Для diarization: HF токен (`HF_TOKEN`) и принятые условия моделей pyannote

## Установка (локально)
```bash
uv venv
uv sync
cp .env.example .env
```

Заполните `.env`:
- `BOT_TOKEN` — токен Telegram бота
- `BOT_API_BASE_URL` — URL локального Bot API server (например `http://localhost:8081`)
- `ROOT_ADMIN_IDS` — ID root‑админов (через запятую)
- `HF_TOKEN` — токен HuggingFace (опционально)
- `STORAGE_PATH` — путь к SQLite (по умолчанию `./data/bot.db`)
- `MEDIA_DIR` — временная папка (по умолчанию `./data/media`)
- `IDLE_SHUTDOWN_MINUTES` — авто‑выключение после простоя
- `BACKEND_FORCE` — `whisperx` или `faster` (опционально)
- `WHISPERX_CMD` — путь к whisperx CLI (опционально)

Запуск:
```bash
uv run python -m transkript_bot.main
```

## Colab
Используйте `colab.ipynb` в корне репозитория:
1. Укажите URL репозитория.
2. Введите `BOT_TOKEN`, `HF_TOKEN`, `ROOT_ADMIN_IDS`.
3. (Опционально) установите `whisperx` для GPU.
4. Запустите бота.

## Локальный Bot API server (для файлов > 20MB)
Официальный Bot API сервер снимает лимит облачного `getFile` (20MB). Пример запуска:
```bash
telegram-bot-api --local --http-port=8081
```
Затем укажите:
```
BOT_API_BASE_URL=http://localhost:8081
```
При переключении с облака на локальный сервер может потребоваться `logOut` (см. документацию Telegram Bot API).

## Использование
- В ЛС: отправьте аудио/видео — получите ответ с очередью и результатом.
- В группах: админ включает бота через `/bot_on`, затем можно отправлять медиа.
- Результат приходит как 3 файла: `.txt`, `.md`, `.json`.

## Примечания
- На Mac (M1/M2/M3) используется CPU‑режим (faster‑whisper).
- Для GPU‑режима нужен установленный WhisperX CLI.
