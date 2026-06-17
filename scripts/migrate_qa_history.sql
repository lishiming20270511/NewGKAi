-- T2.7 补建 qa_history 表（如已存在则跳过）
CREATE TABLE IF NOT EXISTS qa_history (
    id          BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    streamer_id INT UNSIGNED NOT NULL,
    question    VARCHAR(500) NOT NULL,
    answer      TEXT NOT NULL,
    created_at  DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_streamer (streamer_id, created_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
