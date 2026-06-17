-- =============================================================================
-- AI高考志愿规划师 v4.0 数据层迁移脚本
-- 创建日期: 2026-06-17
-- 目标数据库: gaokao_ai
-- 用法: mysql -u root -p gaokao_ai < migrate_v4_data_layer.sql
-- =============================================================================

USE gaokao_ai;

-- ---------------------------------------------------------------------------
-- 1. admin_accounts — 管理员账号（独立于主播体系）
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS admin_accounts (
    id              INT AUTO_INCREMENT PRIMARY KEY,
    username        VARCHAR(64)  NOT NULL UNIQUE COMMENT '管理员用户名',
    password_hash   VARCHAR(255) NOT NULL       COMMENT 'bcrypt哈希(cost=12)',
    role            ENUM('super_admin','admin') NOT NULL DEFAULT 'admin' COMMENT '角色',
    status          ENUM('active','disabled') NOT NULL DEFAULT 'active',
    last_login_at   DATETIME     DEFAULT NULL  COMMENT '最后登录时间',
    created_at      DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at      DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX idx_username (username)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='管理员账号表（独立于主播体系）';

-- ---------------------------------------------------------------------------
-- 2. school_majors — 各校专业列表
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS school_majors (
    id              INT AUTO_INCREMENT PRIMARY KEY,
    school_id       INT          NOT NULL COMMENT '学校ID',
    major_name      VARCHAR(128) NOT NULL COMMENT '专业名称',
    major_level     VARCHAR(32)  DEFAULT NULL COMMENT '专业等级（国家级一流/省级一流/普通）',
    discipline      VARCHAR(64)  DEFAULT NULL COMMENT '学科门类',
    created_at      DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP,
    UNIQUE KEY uk_school_major (school_id, major_name),
    INDEX idx_school (school_id),
    INDEX idx_major (major_name)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='各校开设专业列表';

-- ---------------------------------------------------------------------------
-- 3. major_similarity — 专业相似度映射表
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS major_similarity (
    id              INT AUTO_INCREMENT PRIMARY KEY,
    source_major    VARCHAR(64)  NOT NULL COMMENT '源专业（考生意向）',
    target_major    VARCHAR(64)  NOT NULL COMMENT '目标专业（该校实际开设）',
    similarity      DECIMAL(3,2) NOT NULL DEFAULT 1.00 COMMENT '相似度 0.00-1.00',
    UNIQUE KEY uk_pair (source_major, target_major),
    INDEX idx_source (source_major)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='专业相似度映射表';

-- ---------------------------------------------------------------------------
-- 4. school_tuition — 学费数据（校×专业）
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS school_tuition (
    id              INT AUTO_INCREMENT PRIMARY KEY,
    school_id       INT          NOT NULL COMMENT '学校ID',
    major_name      VARCHAR(128) NOT NULL DEFAULT '__default__' COMMENT '专业名称（通用记录用 __default__）',
    tuition_per_year INT         NOT NULL COMMENT '年学费（元）',
    duration_years  TINYINT      NOT NULL DEFAULT 4 COMMENT '学制（年）',
    data_source     VARCHAR(255) DEFAULT NULL COMMENT '数据来源（学校官网URL）',
    data_year       INT          DEFAULT NULL COMMENT '数据年份',
    created_at      DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at      DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    UNIQUE KEY uk_school_major (school_id, major_name),
    INDEX idx_school (school_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='学费数据表（校×专业）';

-- ---------------------------------------------------------------------------
-- 5. school_employment — 就业数据
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS school_employment (
    id              INT AUTO_INCREMENT PRIMARY KEY,
    school_id       INT          NOT NULL COMMENT '学校ID',
    employment_rate DECIMAL(5,2) DEFAULT NULL COMMENT '就业率(%)',
    graduate_rate   DECIMAL(5,2) DEFAULT NULL COMMENT '深造率(%)',
    data_source     VARCHAR(255) DEFAULT NULL COMMENT '数据来源（教育部报告/学校官网/第三方）',
    data_year       INT          DEFAULT NULL COMMENT '数据年份',
    created_at      DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at      DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    UNIQUE KEY uk_school (school_id),
    INDEX idx_school (school_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='就业数据表';

-- ---------------------------------------------------------------------------
-- 6. school_salary — 薪资数据（校×专业）
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS school_salary (
    id              INT AUTO_INCREMENT PRIMARY KEY,
    school_id       INT          NOT NULL COMMENT '学校ID',
    major_name      VARCHAR(128) NOT NULL DEFAULT '__default__' COMMENT '专业名称（校级通用用 __default__）',
    salary_start_min INT         DEFAULT NULL COMMENT '应届起薪下限（元/月）',
    salary_start_max INT         DEFAULT NULL COMMENT '应届起薪上限（元/月）',
    salary_3yr_min  INT          DEFAULT NULL COMMENT '3年后薪资下限（元/月）',
    salary_3yr_max  INT          DEFAULT NULL COMMENT '3年后薪资上限（元/月）',
    data_source     VARCHAR(255) DEFAULT NULL COMMENT '数据来源',
    data_year       INT          DEFAULT NULL COMMENT '数据年份',
    created_at      DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at      DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    UNIQUE KEY uk_school_major (school_id, major_name),
    INDEX idx_school (school_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='薪资数据表（校×专业）';

-- ---------------------------------------------------------------------------
-- 7. city_analysis — 城市5维分析
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS city_analysis (
    id              INT AUTO_INCREMENT PRIMARY KEY,
    city_name       VARCHAR(32)  NOT NULL UNIQUE COMMENT '城市名称',
    location        TEXT         NOT NULL COMMENT '维度1: 城市位置（地理区位+交通枢纽）',
    advantage       TEXT         NOT NULL COMMENT '维度2: 城市优势（政策/产业/人才）',
    development     TEXT         NOT NULL COMMENT '维度3: 发展现状（GDP/人口/城市等级）',
    main_business   TEXT         NOT NULL COMMENT '维度4: 主要业务（支柱产业/名企）',
    city_level      VARCHAR(16)  DEFAULT NULL COMMENT '城市等级（一线/新一线/二线/…）',
    created_at      DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at      DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='城市5维分析数据表';

-- ---------------------------------------------------------------------------
-- 8. 6类爬虫任务表
-- ---------------------------------------------------------------------------

-- 录取数据爬取任务（已存在，跳过 - 使用旧表 school_admission_crawl_tasks）
-- 注意: school_admission_crawl_tasks 在旧代码中已存在，此处不重建

CREATE TABLE IF NOT EXISTS school_major_crawl_tasks (
    id              INT AUTO_INCREMENT PRIMARY KEY,
    school_id       INT          NOT NULL COMMENT '学校ID',
    school_name     VARCHAR(128) DEFAULT NULL COMMENT '学校名称',
    school_code     VARCHAR(32)  DEFAULT NULL COMMENT '学校代码',
    status          ENUM('pending','running','done','failed') NOT NULL DEFAULT 'pending',
    retry_count     INT          NOT NULL DEFAULT 0,
    error_msg       TEXT         DEFAULT NULL,
    created_at      DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at      DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX idx_status (status),
    INDEX idx_school (school_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='专业数据爬取任务表';

CREATE TABLE IF NOT EXISTS school_tuition_crawl_tasks (
    id              INT AUTO_INCREMENT PRIMARY KEY,
    school_id       INT          NOT NULL COMMENT '学校ID',
    school_name     VARCHAR(128) DEFAULT NULL COMMENT '学校名称',
    school_code     VARCHAR(32)  DEFAULT NULL COMMENT '学校代码',
    status          ENUM('pending','running','done','failed') NOT NULL DEFAULT 'pending',
    retry_count     INT          NOT NULL DEFAULT 0,
    error_msg       TEXT         DEFAULT NULL,
    created_at      DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at      DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX idx_status (status),
    INDEX idx_school (school_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='学费数据爬取任务表';

CREATE TABLE IF NOT EXISTS school_employment_crawl_tasks (
    id              INT AUTO_INCREMENT PRIMARY KEY,
    school_id       INT          NOT NULL COMMENT '学校ID',
    school_name     VARCHAR(128) DEFAULT NULL COMMENT '学校名称',
    school_code     VARCHAR(32)  DEFAULT NULL COMMENT '学校代码',
    status          ENUM('pending','running','done','failed') NOT NULL DEFAULT 'pending',
    retry_count     INT          NOT NULL DEFAULT 0,
    error_msg       TEXT         DEFAULT NULL,
    created_at      DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at      DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX idx_status (status),
    INDEX idx_school (school_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='就业数据爬取任务表';

CREATE TABLE IF NOT EXISTS school_salary_crawl_tasks (
    id              INT AUTO_INCREMENT PRIMARY KEY,
    school_id       INT          NOT NULL COMMENT '学校ID',
    school_name     VARCHAR(128) DEFAULT NULL COMMENT '学校名称',
    school_code     VARCHAR(32)  DEFAULT NULL COMMENT '学校代码',
    status          ENUM('pending','running','done','failed') NOT NULL DEFAULT 'pending',
    retry_count     INT          NOT NULL DEFAULT 0,
    error_msg       TEXT         DEFAULT NULL,
    created_at      DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at      DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX idx_status (status),
    INDEX idx_school (school_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='薪资数据爬取任务表';

CREATE TABLE IF NOT EXISTS school_city_crawl_tasks (
    id              INT AUTO_INCREMENT PRIMARY KEY,
    city_name       VARCHAR(32)  NOT NULL COMMENT '城市名称',
    status          ENUM('pending','running','done','failed') NOT NULL DEFAULT 'pending',
    retry_count     INT          NOT NULL DEFAULT 0,
    error_msg       TEXT         DEFAULT NULL,
    created_at      DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at      DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX idx_status (status),
    INDEX idx_city (city_name)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='城市分析数据爬取任务表';

-- ---------------------------------------------------------------------------
-- 9. 初始化 admin_accounts 默认超级管理员
-- (密码: admin@2026  bcrypt hash 需在应用层生成，此处为占位符)
-- 实际部署时执行: python scripts/seed_admin.py
-- ---------------------------------------------------------------------------
-- INSERT INTO admin_accounts (username, password_hash, role)
-- VALUES ('admin', '$2b$12$PLACEHOLDER_HASH_HERE', 'super_admin');

-- ---------------------------------------------------------------------------
-- 完成
-- ---------------------------------------------------------------------------
SELECT 'v4.0 data layer migration complete' AS result;
