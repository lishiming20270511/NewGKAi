-- ============================================================
-- Migration: PRD v5.3/v5.4 新功能 + 算法升级所需新表
-- 执行顺序: 先备份，再运行本文件，再运行 seed_province_cutoffs.py / seed_broadcast_scripts.py
-- ============================================================

-- ── 省份录取控制线表 ─────────────────────────────────────────

CREATE TABLE IF NOT EXISTS province_cutoffs (
    id               INT AUTO_INCREMENT PRIMARY KEY,
    province         VARCHAR(32) NOT NULL COMMENT '省份',
    subject_category VARCHAR(16) NOT NULL COMMENT '科类（物理/历史/综合）',
    year             INT NOT NULL COMMENT '年份',
    cutoff_yiben     INT DEFAULT NULL COMMENT '一本/本科最低控制线',
    cutoff_zhuanke   INT DEFAULT NULL COMMENT '专科最低控制线',
    created_at       DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at       DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    UNIQUE KEY uk_prov_sub_year (province, subject_category, year),
    INDEX idx_province (province)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='省份录取控制线（一本线/专科线）';


-- ── 省份控制线爬虫任务表 ──────────────────────────────────────

CREATE TABLE IF NOT EXISTS province_cutoff_crawl_tasks (
    id               INT AUTO_INCREMENT PRIMARY KEY,
    province         VARCHAR(32) NOT NULL,
    subject_category VARCHAR(16) NOT NULL,
    year             INT NOT NULL,
    status           ENUM('pending','running','done','failed') NOT NULL DEFAULT 'pending',
    retry_count      INT NOT NULL DEFAULT 0,
    error_msg        TEXT DEFAULT NULL,
    created_at       DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at       DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX idx_status (status),
    INDEX idx_province (province)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='省份控制线爬虫任务表';


-- ── 一次性链接批次表 ─────────────────────────────────────────

CREATE TABLE IF NOT EXISTS one_time_link_batches (
    id           INT AUTO_INCREMENT PRIMARY KEY,
    note         VARCHAR(128) DEFAULT NULL COMMENT '批次备注',
    total_count  INT NOT NULL DEFAULT 0,
    created_by   INT NOT NULL COMMENT '管理员ID',
    created_at   DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='链接批次';


-- ── 一次性链接表 ─────────────────────────────────────────────

CREATE TABLE IF NOT EXISTS one_time_links (
    id           INT AUTO_INCREMENT PRIMARY KEY,
    token        VARCHAR(128) NOT NULL COMMENT 'UUID4.HMAC签名，唯一令牌',
    batch_id     INT NOT NULL COMMENT '批次ID',
    batch_note   VARCHAR(128) DEFAULT NULL COMMENT '批次备注（冗余，方便查询）',
    status       ENUM('active','used','revoked') NOT NULL DEFAULT 'active',
    used_at      DATETIME DEFAULT NULL COMMENT '使用时间',
    used_ip      VARCHAR(45) DEFAULT NULL,
    created_at   DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    UNIQUE KEY uk_token (token),
    INDEX idx_batch (batch_id),
    INDEX idx_status (status)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='一次性报告链接';


-- ── 直播话术脚本表 ───────────────────────────────────────────

CREATE TABLE IF NOT EXISTS broadcast_scripts (
    id           INT AUTO_INCREMENT PRIMARY KEY,
    category     VARCHAR(64) NOT NULL COMMENT '话术分类',
    title        VARCHAR(128) NOT NULL COMMENT '话术标题',
    content      TEXT NOT NULL COMMENT '话术正文',
    sort_order   INT NOT NULL DEFAULT 0 COMMENT '同分类内排序（越小越靠前）',
    is_active    TINYINT NOT NULL DEFAULT 1 COMMENT '是否启用',
    created_at   DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at   DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    UNIQUE KEY uk_category_title (category, title),
    INDEX idx_category (category),
    INDEX idx_sort (category, sort_order)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='直播话术脚本库';
