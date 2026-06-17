# Gaokao AI Data Export

**Export Date**: 2026-06-16
**Source**: MySQL gaokao_ai @ 121.41.69.234:3306
**Format**: CSV (comma-separated, UTF-8, header row included)

## File List

| File | Rows | Size | Description |
|------|------|------|-------------|
| admission_history.csv | 1,171,302 | 89MB | 历年录取数据 |
| yifenyidang.csv | 42,085 | 2.9MB | 一分一段（分数→位次） |
| schools.csv | 2,994 | 186KB | 学校基础信息 |
| school_admission_crawl_tasks.csv | 556 | 56KB | 学校录取爬虫任务 |
| employment_data.csv | 110 | 14KB | 专业就业数据 |
| system_config.csv | 6 | 223B | 系统配置 |
| streamer_accounts.csv | 3 | 438B | 主播账号 |
| streamer_recharge_logs.csv | 3 | 157B | 充值记录 |
| orders.csv | 3 | 694B | 订单 |
| promo_codes.csv | 3 | 182B | 优惠码 |
| users.csv | 2 | 164B | C端用户 |
| report_tasks.csv | 2 | 299B | 报告任务 |

## Crawler Status

- Celery workers: 3 running (since Jun 02)
- crawl_tasks: 0 pending
- school_admission_crawl_tasks: 555 done, 0 pending
- Status: IDLE — all crawl tasks completed
