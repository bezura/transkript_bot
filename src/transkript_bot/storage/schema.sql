CREATE TABLE IF NOT EXISTS users (
    tg_id INTEGER PRIMARY KEY,
    is_allowed INTEGER NOT NULL DEFAULT 0,
    is_blocked INTEGER NOT NULL DEFAULT 0,
    note TEXT,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS chats (
    chat_id INTEGER PRIMARY KEY,
    title TEXT,
    type TEXT,
    enabled INTEGER NOT NULL DEFAULT 0,
    allowed_senders TEXT NOT NULL DEFAULT 'whitelist',
    allowed_user_ids TEXT,
    require_reply INTEGER NOT NULL DEFAULT 0,
    language TEXT NOT NULL DEFAULT 'auto',
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS jobs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    chat_id INTEGER NOT NULL,
    user_id INTEGER NOT NULL,
    message_id INTEGER,
    thread_id INTEGER,
    file_id TEXT,
    file_name TEXT,
    duration_sec REAL,
    backend TEXT,
    status TEXT NOT NULL,
    status_message_id INTEGER,
    progress_message_id INTEGER,
    queued_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    started_at TEXT,
    finished_at TEXT,
    error TEXT,
    output_paths TEXT
);
