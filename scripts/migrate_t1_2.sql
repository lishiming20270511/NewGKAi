-- T1.2 数据库Schema创建与索引优化
-- 执行日期: 2026-06-17
-- 说明: 新架构迁移，重建 orders/report_tasks，创建 crawler_staging/crawler_error_log
-- 执行方式: mysql -h 127.0.0.1 -u gaokao_user -p'gk2026@Pass!' gaokao_ai < migrate_t1_2.sql

SET FOREIGN_KEY_CHECKS = 0;

-- ═══════════════════════════════════════════════════════
-- 1. 旧 orders / report_tasks 归档（保留数据，换名）
-- ═══════════════════════════════════════════════════════
ALTER TABLE report_tasks DROP FOREIGN KEY report_tasks_ibfk_1;
RENAME TABLE report_tasks TO report_tasks_legacy;
RENAME TABLE orders TO orders_legacy;

-- ═══════════════════════════════════════════════════════
-- 2. 新 orders 表（主播扣费订单，与旧B2C表完全不同）
-- ═══════════════════════════════════════════════════════
CREATE TABLE orders (
    id                VARCHAR(32)   NOT NULL                      COMMENT '订单号 GK+时间戳+随机码',
    streamer_id       INT           NOT NULL                      COMMENT '主播ID',
    student_nickname  VARCHAR(64)   NOT NULL                      COMMENT '考生抖音昵称',
    student_province  VARCHAR(32)   NOT NULL                      COMMENT '考生省份',
    student_score     INT           NOT NULL                      COMMENT '高考分数',
    student_subject   VARCHAR(32)   NOT NULL                      COMMENT '选科',
    intended_schools  TEXT          DEFAULT NULL                  COMMENT '意向学校（JSON数组）',
    idempotency_key   VARCHAR(36)   DEFAULT NULL                  COMMENT '幂等键（UUID v4）',
    status            ENUM('unlocked','refunded') NOT NULL DEFAULT 'unlocked',
    created_at        DATETIME      NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (id),
    UNIQUE INDEX uk_idempotency (streamer_id, idempotency_key),
    INDEX idx_streamer_time (streamer_id, created_at),
    INDEX idx_created (created_at),
    CONSTRAINT fk_orders_streamer FOREIGN KEY (streamer_id) REFERENCES streamer_accounts(id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='主播扣费订单表（新架构）';

-- ═══════════════════════════════════════════════════════
-- 3. 新 report_tasks 表（防倒卖检测）
-- ═══════════════════════════════════════════════════════
CREATE TABLE report_tasks (
    id              INT           NOT NULL AUTO_INCREMENT,
    order_id        VARCHAR(32)   NOT NULL  COMMENT '关联订单号',
    streamer_id     INT           NOT NULL  COMMENT '主播ID',
    student_hash    VARCHAR(64)   NOT NULL  COMMENT '考生信息哈希（脱敏）',
    score_range     VARCHAR(16)   NOT NULL  COMMENT '分数段（如560-565）',
    province        VARCHAR(32)   NOT NULL  COMMENT '省份',
    school_hash     VARCHAR(64)   DEFAULT NULL COMMENT '意向学校哈希',
    similarity_flag TINYINT       NOT NULL DEFAULT 0 COMMENT '0=正常 1=疑似 2=告警',
    created_at      DATETIME      NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (id),
    CONSTRAINT fk_rt_order FOREIGN KEY (order_id) REFERENCES orders(id),
    INDEX idx_streamer_time (streamer_id, created_at),
    INDEX idx_hash (student_hash),
    INDEX idx_similarity (similarity_flag)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='报告任务表（防倒卖检测）';

-- ═══════════════════════════════════════════════════════
-- 4. crawler_staging 爬虫暂存表
-- ═══════════════════════════════════════════════════════
CREATE TABLE IF NOT EXISTS crawler_staging (
    id          BIGINT        NOT NULL AUTO_INCREMENT,
    school_id   INT           NOT NULL   COMMENT '学校ID（关联schools.id）',
    major_name  VARCHAR(128)  DEFAULT NULL COMMENT '专业名称',
    year        INT           NOT NULL   COMMENT '录取年份',
    province    VARCHAR(32)   NOT NULL   COMMENT '录取省份',
    category    VARCHAR(16)   DEFAULT NULL COMMENT '科类（物理/历史/综合）',
    batch       VARCHAR(32)   DEFAULT NULL COMMENT '批次',
    min_score   INT           DEFAULT NULL COMMENT '最低分',
    min_rank    INT           DEFAULT NULL COMMENT '最低位次',
    source_ip   VARCHAR(45)   NOT NULL   COMMENT '爬虫服务器IP',
    crawled_at  DATETIME      NOT NULL   COMMENT '爬取时间',
    status      ENUM('pending','validated','rejected','processed') NOT NULL DEFAULT 'pending',
    validated_at DATETIME     DEFAULT NULL COMMENT '校验完成时间',
    error_msg   TEXT          DEFAULT NULL COMMENT '校验错误信息',
    created_at  DATETIME      NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (id),
    INDEX idx_status (status, created_at),
    INDEX idx_school_prov_year (school_id, province, year)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='爬虫数据暂存表';

-- ═══════════════════════════════════════════════════════
-- 5. crawler_error_log 爬虫错误日志表
-- ═══════════════════════════════════════════════════════
CREATE TABLE IF NOT EXISTS crawler_error_log (
    id          BIGINT        NOT NULL AUTO_INCREMENT,
    school_id   INT           DEFAULT NULL COMMENT '学校ID（可能无效）',
    province    VARCHAR(32)   DEFAULT NULL COMMENT '省份',
    year        INT           DEFAULT NULL COMMENT '年份',
    category    VARCHAR(16)   DEFAULT NULL COMMENT '科类',
    raw_data    TEXT          DEFAULT NULL COMMENT '原始提交数据（JSON）',
    error_type  VARCHAR(64)   NOT NULL   COMMENT '错误类型（missing_field/invalid_value/duplicate）',
    error_msg   TEXT          NOT NULL   COMMENT '详细错误信息',
    source_ip   VARCHAR(45)   NOT NULL   COMMENT '来源IP',
    created_at  DATETIME      NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (id),
    INDEX idx_created (created_at),
    INDEX idx_error_type (error_type)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='爬虫数据错误日志表';

-- ═══════════════════════════════════════════════════════
-- 6. system_config 预置配置数据
-- ═══════════════════════════════════════════════════════
-- 使用现有列名 key_/value_（保持兼容，T1.4 代码按此读取）
INSERT INTO system_config (key_, value_, updated_at) VALUES
    ('score_max',         '{"上海":660,"其他":750}',      NOW()),
    ('tier_thresholds',   '{"boost":30,"solid":60,"safe":85,"low_score":5}', NOW()),
    ('price_per_query',   '29.9',                        NOW()),
    ('low_score_boundary','400',                          NOW()),
    ('max_candidates',    '105',                          NOW())
ON DUPLICATE KEY UPDATE
    value_     = VALUES(value_),
    updated_at = NOW();

SET FOREIGN_KEY_CHECKS = 1;

-- ═══════════════════════════════════════════════════════
-- 7. 验证：索引确认 + EXPLAIN 测试
-- ═══════════════════════════════════════════════════════
-- admission_history 已有 idx_school_query(school_id, province, year, category) 覆盖需求
-- yifenyidang 已有 uk_record(province, year, category, score) 覆盖需求
EXPLAIN SELECT cumulative_count FROM yifenyidang
WHERE province='河南' AND year=2025 AND category='理科' AND score<=580
ORDER BY score DESC LIMIT 1;
