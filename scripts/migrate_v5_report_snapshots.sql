-- 报告快照表：保存每次推荐结果，供管理员补发PDF
-- 执行方式：mysql -u root -p gaokao_ai < scripts/migrate_v5_report_snapshots.sql

CREATE TABLE IF NOT EXISTS report_snapshots (
    id               INT AUTO_INCREMENT PRIMARY KEY,
    order_id         VARCHAR(32)  DEFAULT NULL COMMENT '主播扣费订单号（主播端流程）',
    link_token       VARCHAR(128) DEFAULT NULL COMMENT '一次性链接token（学生端流程）',
    streamer_id      INT          DEFAULT NULL,
    student_nickname VARCHAR(64)  DEFAULT NULL,
    student_province VARCHAR(32)  DEFAULT NULL,
    student_score    INT          DEFAULT NULL,
    student_input    JSON         NOT NULL COMMENT '完整请求参数',
    recommendation_result JSON   NOT NULL COMMENT '完整推荐结果',
    created_at       DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_order_id  (order_id),
    INDEX idx_link_token (link_token),
    INDEX idx_created   (created_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='推荐报告快照，用于管理员补发PDF';
