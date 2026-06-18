# AI高考志愿规划师 · 开发说明

## 项目状态
当前版本：**v5.7**（已验收，PDF风格通过）  
代码仓库：`https://github.com/lishiming20270511/NewGKAi`  
生产服务器：`121.41.69.234`，路径 `/root/gaokao-ai/`

## 技术栈
- **前端**：单文件 SPA `frontend/index.html`（所有 JS/CSS 内联，无构建步骤）
- **后端**：FastAPI（Python）`api/` 目录，入口 `main.py`
- **数据库**：MySQL + Redis
- **PDF**：jsPDF 2.5.1 + html2canvas 1.4.1（方案A：全HTML渲染→截图→PDF）

## 开发原则（严格遵守）
1. **不改动已验收的功能**：PDF生成、学校推荐展示、登录认证流程 — 除非明确被要求修改
2. **单文件前端**：所有前端改动只在 `frontend/index.html` 中，不新建 JS/CSS 文件
3. **最小改动**：只改任务要求的部分，不顺手重构周边代码
4. **改前先读**：修改任何函数前，先读该函数及其调用方的完整代码
5. **语法验证**：每次修改 index.html 后，用以下命令验证 JS 语法：
   ```bash
   python3 -c "
   import re
   content = open('frontend/index.html', encoding='utf-8').read()
   scripts = re.findall(r'<script(?![^>]*src)[^>]*>(.*?)</script>', content, re.DOTALL)
   open('C:/tmp/_check.js','w',encoding='utf-8').write('\n'.join(scripts))
   "
   node --check C:/tmp/_check.js
   ```

## 部署流程
```bash
# 推送 GitHub（需代理 127.0.0.1:10808 在线）
cd D:/dev/NewGKAi && git push origin main

# 部署生产服务器
scp -i ~/.ssh/id_rsa frontend/index.html root@121.41.69.234:/root/gaokao-ai/frontend/index.html
```

## 已知问题（待处理）
> 见 `docs/BBB.txt` 和 `docs/abc.txt`，或直接询问

## 关键文件
| 文件 | 用途 |
|------|------|
| `frontend/index.html` | 全部前端（唯一前端文件） |
| `api/services/recommendation.py` | 推荐算法核心 |
| `api/routers/` | API 路由 |
| `docs/PRD_v5.md` | 最新需求文档 |
| `docs/Progress.md` | 开发进度记录 |

## 提交规范
```bash
git add <具体文件>  # 不用 git add -A
git commit -m "vX.X: 简短说明（中文）"
git push origin main
```
