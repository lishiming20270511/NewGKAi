# PDF报告重设计实施计划 — 方案A（全HTML渲染）

> **For agentic workers:** REQUIRED SUB-SKILL: Use `superpowers:subagent-driven-development` (recommended) or `superpowers:executing-plans` to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 把 `frontend/index.html` 的 PDF 下载功能，从现有的"简单封面 + jsPDF文字内页"完整替换为与 `docs/pdf_preview.html` 视觉完全一致的深蓝金色多页A4报告。

**Architecture:** 每页报告构建为一个 595×842px 的 HTML div 字符串，注入屏幕外隐藏容器 `#pdfCoverZone`，由 `html2canvas(scale:3)` 截图后 `pdf.addImage()` 叠入 jsPDF，循环直至全部页完成后 `pdf.save()`。共 9 个页面构建函数 + 1 个渲染辅助函数 + 1 个主控函数。

**Tech Stack:** jsPDF 2.5.1、html2canvas 1.4.1、qrcodejs（均已在 `index.html` `<head>` 中 CDN 引入，无需额外安装）

**视觉标准：** `docs/pdf_preview.html`——开发全程在浏览器中对照此文件，以肉眼一致为验收标准。

---

## 文件改动范围（只动 `frontend/index.html`）

| 操作 | 行号 | 说明 |
|------|------|------|
| 修改 | ~246 行 `#pdfCoverZone` CSS | 宽度从 `375px` 改为 `595px`，`min-height` 改为 `842px` |
| 新增 | 1606 行 PDF 区块开头 | `PDF_STYLES` 常量 + `renderPageToCanvas()` + 9个页面构建函数 |
| 删除 | 1610–1654 行 | `extractTextBlocks()` 全部删除 |
| 替换 | 1655–1845 行 | `downloadPDF()` 旧逻辑全部替换为新版 |
| 删除 | 1863–1910 行 | `buildCoverHTML()` 全部删除 |
| 保留 | 1847–1861 行 | `addDiagonalWatermarks()` 保留不动（PDF水印仍使用） |
| 保留 | 2028 行 | `<div id="pdfCoverZone"></div>` DOM元素保留，仅改CSS |

---

## Task 1：改 `#pdfCoverZone` 尺寸 + 添加 `PDF_STYLES` 常量 + `renderPageToCanvas()`

**Files:**
- Modify: `frontend/index.html:246`（CSS，`#pdfCoverZone` 规则）
- Modify: `frontend/index.html:1606`（JS，PDF Generation 区块开头）

### 背景

现有 `#pdfCoverZone` 宽375px（手机比例），新版PDF为A4竖版595px。
`PDF_STYLES` 是从 `docs/pdf_preview.html` 的 `<style>` 块提取的所有 CSS class 定义，注入每页 HTML 字符串的 `<style>` 标签内，使页面样式与预览图完全一致。
`renderPageToCanvas()` 是所有页面共用的截图辅助函数。

- [ ] **Step 1：修改 `#pdfCoverZone` CSS**

找到 `index.html` 约第246行：
```css
#pdfCoverZone{position:fixed;top:-9999px;left:-9999px;visibility:hidden;width:375px;z-index:-1}
```
替换为：
```css
#pdfCoverZone{position:fixed;top:-9999px;left:-9999px;visibility:hidden;width:595px;min-height:842px;z-index:-1;overflow:hidden}
```

- [ ] **Step 2：在第1606行 `// ══ PDF Generation` 注释之后，旧代码之前，插入 `PDF_STYLES` 常量**

```javascript
// ══════════════════════════════════════════════════════════
// PDF Generation v2 — 方案A：全HTML渲染 → html2canvas → jsPDF
// 视觉标准：docs/pdf_preview.html
// ══════════════════════════════════════════════════════════

const PDF_STYLES = `
* { margin:0; padding:0; box-sizing:border-box; }
body { font-family:"PingFang SC","Microsoft YaHei","Noto Sans SC",sans-serif; }
.page { width:595px; min-height:842px; position:relative; overflow:hidden; }
/* 封面 */
.cover { background:#091630; display:flex; flex-direction:column; }
.cover-header { display:flex; align-items:center; justify-content:space-between; padding:20px 28px 16px; border-bottom:1px solid rgba(200,168,72,0.25); position:relative; z-index:2; }
.cover-logo { display:flex; align-items:center; gap:10px; }
.cover-logo-icon { width:36px; height:36px; background:linear-gradient(135deg,#C9A84C,#F0D060); border-radius:8px; display:flex; align-items:center; justify-content:center; font-size:18px; }
.cover-logo-text .name { font-size:14px; font-weight:700; color:#F0E0A0; letter-spacing:0.5px; display:block; }
.cover-logo-text .sub { font-size:10px; color:rgba(200,168,72,0.7); letter-spacing:1px; display:block; }
.cover-report-num { font-size:11px; color:rgba(200,168,72,0.6); font-family:monospace; }
.cover-body { flex:1; padding:30px 40px 0; position:relative; overflow:hidden; }
.cover-title-top { font-size:13px; color:rgba(200,168,72,0.8); letter-spacing:3px; margin-bottom:12px; }
.cover-title-main { font-size:36px; font-weight:900; color:#FFFFFF; line-height:1.25; letter-spacing:2px; }
.cover-title-sub { font-size:24px; font-weight:700; color:#C9A84C; letter-spacing:6px; margin-top:8px; }
.cover-divider { width:64px; height:3px; background:linear-gradient(90deg,#C9A84C,rgba(200,168,72,0.2)); margin:20px 0; }
.cover-tagline { font-size:13px; color:rgba(200,200,220,0.75); line-height:1.7; }
.cover-footer { padding:18px 28px 22px; display:flex; align-items:center; justify-content:space-between; border-top:1px solid rgba(200,168,72,0.2); background:rgba(0,0,0,0.3); position:relative; z-index:2; }
.cover-warning { font-size:11px; color:rgba(200,168,72,0.7); line-height:1.5; }
.cover-warning .sub { margin-top:3px; font-size:10px; color:rgba(200,168,72,0.5); }
.cover-qr { width:64px; height:64px; background:white; border-radius:4px; overflow:hidden; }
/* 内页通用 */
.inner-page { background:#FFFFFF; display:flex; flex-direction:column; }
.inner-header { display:flex; align-items:center; justify-content:space-between; padding:12px 24px; background:#091630; border-bottom:3px solid #C9A84C; flex-shrink:0; }
.inner-header .logo-wrap { display:flex; align-items:center; gap:8px; }
.inner-header .logo-icon { width:26px; height:26px; background:linear-gradient(135deg,#C9A84C,#F0D060); border-radius:5px; display:flex; align-items:center; justify-content:center; font-size:13px; }
.inner-header .logo-text { font-size:13px; font-weight:700; color:#F0E0A0; }
.inner-header .header-right { font-size:10px; color:rgba(200,168,72,0.7); font-family:monospace; }
.inner-body { flex:1; padding:18px 24px 14px; position:relative; z-index:2; }
.inner-footer { display:flex; align-items:center; justify-content:space-between; padding:8px 24px; background:#F8F9FB; border-top:1px solid #E5E7EB; font-size:10px; color:#9CA3AF; flex-shrink:0; }
.inner-footer .report-id { font-family:monospace; color:#6B7280; }
.inner-footer .wm { font-size:9px; color:#C9A84C; font-weight:600; }
/* 斜纹水印 */
.diag-wm { position:absolute; top:0; left:0; right:0; bottom:0; pointer-events:none; z-index:1; background:repeating-linear-gradient(-35deg,transparent,transparent 80px,rgba(200,168,72,0.025) 80px,rgba(200,168,72,0.025) 82px); }
/* 区块标题 */
.sec-title { display:flex; align-items:center; gap:8px; font-size:14px; font-weight:700; color:#091630; margin-bottom:10px; padding-bottom:6px; border-bottom:2px solid #E9ECEF; }
.sec-badge { font-size:10px; font-weight:600; color:white; background:#091630; padding:2px 7px; border-radius:3px; }
/* 考生信息卡 */
.stu-card { background:#F0F4FF; border:1px solid #C7D5F0; border-left:4px solid #1E3A8A; border-radius:6px; padding:14px 16px; margin-bottom:14px; }
.stu-grid { display:grid; grid-template-columns:1fr 1fr 1fr; gap:10px 16px; }
.stu-field label { font-size:10px; color:#6B7280; display:block; margin-bottom:2px; }
.stu-field .val { font-size:13px; font-weight:600; color:#1F2937; }
.stu-field .val.hi { color:#1E3A8A; font-size:15px; font-family:monospace; }
/* 权威保障卡 */
.auth-card { background:#FFFBF0; border:1px solid #FDE68A; border-left:4px solid #D97706; border-radius:6px; padding:12px 14px; margin-bottom:14px; }
.auth-item { display:flex; align-items:flex-start; gap:8px; font-size:11.5px; color:#374151; line-height:1.6; margin-bottom:6px; }
.auth-item:last-child { margin-bottom:0; }
.auth-dot { width:6px; height:6px; background:#D97706; border-radius:50%; flex-shrink:0; margin-top:5px; }
/* 警告横幅 */
.warn-banner { background:#FEF2F2; border:1px solid #FECACA; border-left:4px solid #DC2626; border-radius:6px; padding:10px 14px; margin-bottom:14px; display:flex; align-items:center; gap:8px; font-size:11.5px; color:#991B1B; font-weight:600; }
/* 定位分析 */
.pos-grid4 { display:grid; grid-template-columns:repeat(4,1fr); gap:8px; margin-bottom:12px; }
.pos-card { background:#F9FAFB; border:1px solid #E5E7EB; border-radius:6px; padding:10px 12px; }
.pos-card .pc-label { font-size:10px; color:#6B7280; margin-bottom:3px; }
.pos-card .pc-val { font-size:15px; font-weight:700; }
.pos-card .pc-sub { font-size:10px; color:#9CA3AF; margin-top:2px; }
/* Tier分层 */
.tier-row { display:flex; gap:8px; margin-bottom:12px; }
.tier-blk { flex:1; border-radius:6px; padding:10px 12px; text-align:center; }
.tier-blk.rush { background:#FEF2F2; border:1px solid #FECACA; }
.tier-blk.stable { background:#EFF6FF; border:1px solid #BFDBFE; }
.tier-blk.safe { background:#F0FDF4; border:1px solid #BBF7D0; }
.tier-lbl { font-size:10px; font-weight:700; margin-bottom:4px; }
.tier-blk.rush .tier-lbl { color:#DC2626; }
.tier-blk.stable .tier-lbl { color:#2563EB; }
.tier-blk.safe .tier-lbl { color:#16A34A; }
.tier-cnt { font-size:20px; font-weight:900; color:#111827; }
.tier-prob { font-size:10px; color:#6B7280; }
/* 特别关注区 */
.special-zone { background:#FFFBEB; border:1px solid #FDE68A; border-left:4px solid #F59E0B; border-radius:6px; padding:12px 14px; margin-bottom:14px; }
.sp-row { display:flex; align-items:center; justify-content:space-between; padding:6px 0; border-bottom:1px solid rgba(245,158,11,0.2); }
.sp-row:last-child { border-bottom:none; }
/* 学校卡片 */
.school-card { border:1px solid #E5E7EB; border-radius:8px; margin-bottom:12px; overflow:hidden; }
.sc-hd { padding:10px 14px; display:flex; align-items:center; justify-content:space-between; }
.sc-hd.rush { background:linear-gradient(135deg,#FEF2F2,#FFF5F5); border-bottom:2px solid #FECACA; }
.sc-hd.stable { background:linear-gradient(135deg,#EFF6FF,#F5F9FF); border-bottom:2px solid #BFDBFE; }
.sc-hd.safe { background:linear-gradient(135deg,#F0FDF4,#F5FFF7); border-bottom:2px solid #BBF7D0; }
.sc-name { font-size:15px; font-weight:800; color:#111827; }
.sc-badges { display:flex; gap:4px; flex-wrap:wrap; margin-top:4px; }
.prob-area { text-align:right; }
.prob-big { font-size:22px; font-weight:900; font-family:monospace; }
.prob-big.rush { color:#DC2626; }
.prob-big.stable { color:#2563EB; }
.prob-big.safe { color:#16A34A; }
.prob-bar { width:80px; height:5px; background:#E5E7EB; border-radius:3px; margin-top:4px; overflow:hidden; margin-left:auto; }
.prob-fill { height:100%; border-radius:3px; }
.prob-fill.rush { background:#EF4444; }
.prob-fill.stable { background:#3B82F6; }
.prob-fill.safe { background:#22C55E; }
.sc-body { padding:10px 14px; background:#FFFFFF; }
.dim-grid { display:grid; grid-template-columns:1fr 1fr; gap:4px 14px; }
.dim-item { padding:4px 0; border-bottom:1px solid #F3F4F6; }
.dim-item:last-child { border-bottom:none; }
.dim-lbl { font-size:9.5px; color:#9CA3AF; font-weight:500; }
.dim-val { font-size:11.5px; color:#374151; font-weight:500; line-height:1.5; }
.dim-val.mono { font-family:monospace; font-size:12px; }
.ai-cmt { margin-top:8px; padding:7px 10px; background:#F9FAFB; border-left:3px solid #818CF8; font-size:11px; color:#4B5563; font-style:italic; line-height:1.6; }
.risk-box { margin-top:8px; padding:8px 10px; background:#FFF7ED; border:1px solid #FED7AA; border-radius:4px; }
.risk-title { font-size:10px; font-weight:700; color:#C2410C; margin-bottom:4px; }
.risk-grid { display:grid; grid-template-columns:1fr 1fr 1fr; gap:4px; }
.risk-item { font-size:10px; color:#6B7280; }
.risk-high { color:#DC2626; font-weight:700; }
.risk-mid { color:#D97706; font-weight:700; }
.risk-low { color:#16A34A; font-weight:700; }
.enroll-box { margin-top:8px; }
.enroll-lbl { font-size:10px; font-weight:700; color:#374151; margin-bottom:4px; }
.enroll-table { width:100%; border-collapse:collapse; font-size:10px; }
.enroll-table th { background:#F3F4F6; color:#6B7280; padding:3px 5px; font-weight:600; border:1px solid #E5E7EB; }
.enroll-table td { padding:3px 5px; border:1px solid #E5E7EB; text-align:center; color:#374151; }
.enroll-shrink { color:#DC2626; font-weight:700; }
/* Badge */
.badge { font-size:9px; font-weight:700; padding:1px 5px; border-radius:3px; }
.b985 { background:#FEF3C7; color:#D97706; }
.b211 { background:#EDE9FE; color:#7C3AED; }
.bdf { background:#ECFEFF; color:#0E7490; }
.br { background:#FEF2F2; color:#DC2626; }
.bs { background:#EFF6FF; color:#2563EB; }
.bsafe { background:#F0FDF4; color:#16A34A; }
.bpub { background:#F3F4F6; color:#374151; }
.bicy { background:#FFF7ED; color:#C2410C; }
/* 对比表 */
.cmp-table { width:100%; border-collapse:collapse; font-size:10px; margin-bottom:12px; }
.cmp-table th { background:#091630; color:#F0E0A0; padding:6px 6px; text-align:center; font-weight:600; font-size:10px; white-space:nowrap; }
.cmp-table td { padding:5px 6px; border:1px solid #E5E7EB; text-align:center; color:#374151; font-size:10px; }
.cmp-table tr:nth-child(even) td { background:#F9FAFB; }
.cmp-group td { background:#F3F4F6!important; font-weight:700; color:#1F2937; font-size:10.5px; }
.cmp-rush { color:#DC2626; font-weight:700; }
.cmp-stable { color:#2563EB; font-weight:700; }
.cmp-safe { color:#16A34A; font-weight:700; }
.cmp-name { text-align:left!important; font-weight:600; color:#111827; }
/* 建议书 */
.sug-sec { margin-bottom:14px; }
.sug-title { font-size:12px; font-weight:700; color:#1E3A8A; padding:6px 10px; background:#EFF6FF; border-left:3px solid #2563EB; border-radius:0 4px 4px 0; margin-bottom:8px; }
.sug-text { font-size:11.5px; color:#374151; line-height:1.8; }
.sug-item { display:flex; align-items:flex-start; gap:8px; margin-bottom:6px; font-size:11.5px; color:#374151; line-height:1.7; }
.sug-num { width:18px; height:18px; background:#1E3A8A; color:white; border-radius:50%; display:flex; align-items:center; justify-content:center; font-size:10px; font-weight:700; flex-shrink:0; margin-top:1px; }
.grad-box { background:linear-gradient(135deg,#F0F4FF,#EFF6FF); border:1px solid #BFDBFE; border-radius:6px; padding:12px 14px; margin-top:10px; }
.grad-title { font-size:12px; font-weight:700; color:#1E3A8A; margin-bottom:8px; }
.grad-row { display:flex; align-items:flex-start; gap:8px; margin-bottom:6px; font-size:11px; color:#374151; }
.gb-r { font-size:9.5px; font-weight:700; padding:2px 6px; border-radius:3px; background:#FEF2F2; color:#DC2626; flex-shrink:0; margin-top:1px; }
.gb-s { font-size:9.5px; font-weight:700; padding:2px 6px; border-radius:3px; background:#EFF6FF; color:#2563EB; flex-shrink:0; margin-top:1px; }
.gb-b { font-size:9.5px; font-weight:700; padding:2px 6px; border-radius:3px; background:#F0FDF4; color:#16A34A; flex-shrink:0; margin-top:1px; }
/* 免责 */
.disc-card { background:#F9FAFB; border:1px solid #E5E7EB; border-radius:6px; padding:14px 16px; font-size:11px; color:#6B7280; line-height:1.8; margin-bottom:12px; }
.disc-title { font-size:13px; font-weight:700; color:#1F2937; margin-bottom:8px; }
/* 方案结构一览 */
.struct-grid { display:grid; grid-template-columns:1fr 1fr; gap:6px; }
.struct-item { padding:6px 8px; background:#F3F4F6; border-radius:4px; display:flex; align-items:center; gap:6px; font-size:11px; color:#374151; }
.struct-item .lbl { color:#1E3A8A; font-weight:700; }
`;
```

- [ ] **Step 3：在 `PDF_STYLES` 之后，紧接插入 `renderPageToCanvas()` 辅助函数**

```javascript
/**
 * 将 HTML 字符串注入 #pdfCoverZone，html2canvas 截图后返回 canvas。
 * 截图完毕后自动清空容器。
 */
async function renderPageToCanvas(html) {
  const zone = document.getElementById('pdfCoverZone');
  zone.innerHTML = html;
  zone.style.visibility = 'visible';
  await new Promise(r => setTimeout(r, 150));   // 等待字体/图片渲染
  const canvas = await html2canvas(zone, {
    scale: 3,
    useCORS: true,
    backgroundColor: null,
    logging: false,
    width: 595,
    windowWidth: 595,
    scrollX: 0,
    scrollY: 0
  });
  zone.style.visibility = 'hidden';
  zone.innerHTML = '';
  return canvas;
}
```

- [ ] **Step 4：浏览器验证**

在 Chrome DevTools Console 执行：
```javascript
renderPageToCanvas('<div style="width:595px;height:200px;background:#091630;color:#C9A84C;font-size:24px;display:flex;align-items:center;justify-content:center;">TEST 595px</div>').then(c => { document.body.appendChild(c); });
```
预期：页面顶部出现一个深蓝色宽595px的canvas，文字"TEST 595px"金色可见。

---

## Task 2：实现 `buildCoverPage()`（封面页）

**Files:**
- Modify: `frontend/index.html`（Task 1 代码之后继续追加）

### 背景

对照 `docs/pdf_preview.html` 封面页结构：深蓝底 `#091630` + 金色装饰 SVG 弧线 + 顶部 Logo 行 + 主标题 + SVG大学建筑插图 + 底部 QR 码区。
`qrDataUrl` 为 base64 PNG 字符串（可能为 null，null 时显示空白占位框）。

- [ ] **Step 1：追加 `buildCoverPage()` 函数**

```javascript
/**
 * 封面页 HTML（595×842px，深蓝金色风格）
 * @param {object} stu  - S.student
 * @param {string} reportId
 * @param {string|null} qrDataUrl  - base64 PNG
 * @param {string} ts   - 格式如 "2026年6月18日 11:39"
 */
function buildCoverPage(stu, reportId, qrDataUrl, ts) {
  const nickname = esc(stu.nickname || '考生');
  const province = esc(stu.province || '—');
  const score    = Number(stu.score) || '—';
  const rank     = esc(String(stu.rank || '估算中'));
  const subj     = esc(stu.subjectStr || stu.subject_str || '—');
  const rid      = esc(reportId);
  const qrImg    = qrDataUrl
    ? `<img src="${qrDataUrl}" style="width:56px;height:56px;display:block;border-radius:3px;">`
    : `<div style="width:56px;height:56px;background:#D0D8E8;border-radius:3px;"></div>`;

  return `<html><head><meta charset="UTF-8"><style>${PDF_STYLES}</style></head><body>
<div class="page cover" style="width:595px;min-height:842px;">
  <!-- SVG装饰背景 -->
  <svg style="position:absolute;top:0;left:0;width:100%;height:100%;z-index:0;pointer-events:none;" viewBox="0 0 595 842" fill="none">
    <defs>
      <radialGradient id="g1" cx="15%" cy="85%" r="55%">
        <stop offset="0%" stop-color="#1E40AF" stop-opacity="0.3"/>
        <stop offset="100%" stop-color="#091630" stop-opacity="0"/>
      </radialGradient>
      <radialGradient id="g2" cx="90%" cy="10%" r="40%">
        <stop offset="0%" stop-color="#C9A84C" stop-opacity="0.08"/>
        <stop offset="100%" stop-color="#091630" stop-opacity="0"/>
      </radialGradient>
    </defs>
    <rect width="595" height="842" fill="url(#g1)"/>
    <rect width="595" height="842" fill="url(#g2)"/>
    <path d="M -20 660 Q 120 540 280 600 Q 440 660 620 560" stroke="#C9A84C" stroke-width="1.5" stroke-opacity="0.6" fill="none"/>
    <path d="M -20 700 Q 100 590 260 645 Q 420 700 640 600" stroke="#C9A84C" stroke-width="0.8" stroke-opacity="0.35" fill="none"/>
    <path d="M -20 740 Q 80 640 240 690 Q 400 740 660 640" stroke="#C9A84C" stroke-width="0.5" stroke-opacity="0.2" fill="none"/>
    <line x1="560" y1="60" x2="560" y2="310" stroke="#C9A84C" stroke-width="0.5" stroke-opacity="0.25"/>
    <circle cx="120" cy="400" r="1.5" fill="#C9A84C" fill-opacity="0.5"/>
    <circle cx="320" cy="360" r="1" fill="#C9A84C" fill-opacity="0.4"/>
    <circle cx="480" cy="420" r="1.5" fill="#C9A84C" fill-opacity="0.35"/>
  </svg>

  <!-- 页眉 -->
  <div class="cover-header">
    <div class="cover-logo">
      <div class="cover-logo-icon">🎓</div>
      <div class="cover-logo-text">
        <span class="name">AI高考志愿规划师</span>
        <span class="sub">AI-Powered Admission Advisor · GKZS</span>
      </div>
    </div>
    <span class="cover-report-num">报告编号：${rid}</span>
  </div>

  <!-- 主体 -->
  <div class="cover-body">
    <div style="position:relative;z-index:2;margin-top:28px;">
      <div class="cover-title-top">GAOKAO VOLUNTEER PLANNING REPORT</div>
      <div class="cover-title-main">AI高考志愿<br>规划师</div>
      <div class="cover-title-sub">志愿规划报告书</div>
      <div class="cover-divider"></div>
      <div class="cover-tagline">
        深耕近6年全国2200万+真实录取数据<br>
        Claude · DeepSeek V4 Pro · GPT-5.5 交叉综合分析<br>
        精准定位 · 拒绝滑档 · 把分数变成录取通知书
      </div>
    </div>
    <!-- 大学建筑 SVG 插图 -->
    <div style="position:relative;z-index:2;margin-top:24px;display:flex;justify-content:center;">
      <svg width="340" height="155" viewBox="0 0 340 160" fill="none">
        <rect x="120" y="40" width="100" height="110" stroke="#C9A84C" stroke-width="1.2" fill="rgba(200,168,72,0.05)"/>
        <rect x="145" y="100" width="50" height="50" stroke="#C9A84C" stroke-width="1" fill="rgba(200,168,72,0.03)"/>
        <line x1="155" y1="100" x2="155" y2="150" stroke="#C9A84C" stroke-width="0.8"/>
        <line x1="170" y1="100" x2="170" y2="150" stroke="#C9A84C" stroke-width="0.8"/>
        <line x1="185" y1="100" x2="185" y2="150" stroke="#C9A84C" stroke-width="0.8"/>
        <polygon points="120,40 220,40 170,8" stroke="#C9A84C" stroke-width="1.2" fill="rgba(200,168,72,0.08)"/>
        <line x1="170" y1="8" x2="170" y2="-2" stroke="#C9A84C" stroke-width="0.8"/>
        <polygon points="170,-2 178,3 170,8" fill="#C9A84C" fill-opacity="0.8"/>
        <rect x="40" y="70" width="75" height="80" stroke="#C9A84C" stroke-width="0.8" stroke-opacity="0.7" fill="rgba(200,168,72,0.03)"/>
        <rect x="225" y="70" width="75" height="80" stroke="#C9A84C" stroke-width="0.8" stroke-opacity="0.7" fill="rgba(200,168,72,0.03)"/>
        <rect x="55" y="80" width="14" height="14" stroke="#C9A84C" stroke-width="0.6" stroke-opacity="0.6" fill="rgba(200,168,72,0.08)"/>
        <rect x="75" y="80" width="14" height="14" stroke="#C9A84C" stroke-width="0.6" stroke-opacity="0.6" fill="rgba(200,168,72,0.08)"/>
        <rect x="95" y="80" width="14" height="14" stroke="#C9A84C" stroke-width="0.6" stroke-opacity="0.6" fill="rgba(200,168,72,0.08)"/>
        <rect x="55" y="102" width="14" height="14" stroke="#C9A84C" stroke-width="0.6" stroke-opacity="0.6" fill="rgba(200,168,72,0.08)"/>
        <rect x="75" y="102" width="14" height="14" stroke="#C9A84C" stroke-width="0.6" stroke-opacity="0.6" fill="rgba(200,168,72,0.08)"/>
        <rect x="95" y="102" width="14" height="14" stroke="#C9A84C" stroke-width="0.6" stroke-opacity="0.6" fill="rgba(200,168,72,0.08)"/>
        <rect x="236" y="80" width="14" height="14" stroke="#C9A84C" stroke-width="0.6" stroke-opacity="0.6" fill="rgba(200,168,72,0.08)"/>
        <rect x="256" y="80" width="14" height="14" stroke="#C9A84C" stroke-width="0.6" stroke-opacity="0.6" fill="rgba(200,168,72,0.08)"/>
        <rect x="276" y="80" width="14" height="14" stroke="#C9A84C" stroke-width="0.6" stroke-opacity="0.6" fill="rgba(200,168,72,0.08)"/>
        <rect x="236" y="102" width="14" height="14" stroke="#C9A84C" stroke-width="0.6" stroke-opacity="0.6" fill="rgba(200,168,72,0.08)"/>
        <rect x="256" y="102" width="14" height="14" stroke="#C9A84C" stroke-width="0.6" stroke-opacity="0.6" fill="rgba(200,168,72,0.08)"/>
        <rect x="276" y="102" width="14" height="14" stroke="#C9A84C" stroke-width="0.6" stroke-opacity="0.6" fill="rgba(200,168,72,0.08)"/>
        <rect x="132" y="55" width="16" height="14" stroke="#C9A84C" stroke-width="0.7" stroke-opacity="0.8" fill="rgba(200,168,72,0.1)"/>
        <rect x="153" y="55" width="16" height="14" stroke="#C9A84C" stroke-width="0.7" stroke-opacity="0.8" fill="rgba(200,168,72,0.1)"/>
        <rect x="174" y="55" width="16" height="14" stroke="#C9A84C" stroke-width="0.7" stroke-opacity="0.8" fill="rgba(200,168,72,0.1)"/>
        <rect x="195" y="55" width="16" height="14" stroke="#C9A84C" stroke-width="0.7" stroke-opacity="0.8" fill="rgba(200,168,72,0.1)"/>
        <rect x="132" y="76" width="16" height="14" stroke="#C9A84C" stroke-width="0.7" stroke-opacity="0.8" fill="rgba(200,168,72,0.1)"/>
        <rect x="195" y="76" width="16" height="14" stroke="#C9A84C" stroke-width="0.7" stroke-opacity="0.8" fill="rgba(200,168,72,0.1)"/>
        <line x1="20" y1="150" x2="320" y2="150" stroke="#C9A84C" stroke-width="1" stroke-opacity="0.4"/>
        <line x1="22" y1="150" x2="22" y2="125" stroke="#C9A84C" stroke-width="0.8" stroke-opacity="0.5"/>
        <circle cx="22" cy="118" r="8" stroke="#C9A84C" stroke-width="0.6" fill="rgba(200,168,72,0.06)" stroke-opacity="0.5"/>
        <line x1="316" y1="150" x2="316" y2="125" stroke="#C9A84C" stroke-width="0.8" stroke-opacity="0.5"/>
        <circle cx="316" cy="118" r="8" stroke="#C9A84C" stroke-width="0.6" fill="rgba(200,168,72,0.06)" stroke-opacity="0.5"/>
      </svg>
    </div>
  </div>

  <!-- 底部 -->
  <div class="cover-footer">
    <div class="cover-warning">
      <div>⚠ 严禁倒卖 · 本内容由高考志愿规划师专业制作</div>
      <div class="sub">考生昵称：${nickname} · ${province} · ${score}分 · 位次 ${rank}</div>
      <div class="sub">选科：${subj} · 生成时间：${esc(ts)}</div>
    </div>
    <div class="cover-qr">${qrImg}</div>
  </div>
</div>
</body></html>`;
}
```

- [ ] **Step 2：浏览器验证**

打开 `index.html`，登录，生成一份报告，然后在 Console 执行：
```javascript
renderPageToCanvas(buildCoverPage(S.student, 'GK-TEST-001', null, '2026年6月18日 11:39'))
  .then(c => { c.style.cssText='position:fixed;top:0;left:0;width:300px;z-index:9999;'; document.body.appendChild(c); });
```
预期：页面左上角出现深蓝金色封面缩略图，布局与 `pdf_preview.html` 封面一致。

---

## Task 3：实现 `buildInnerPage()` 通用包装器 + `buildInfoPage()`（第1页）

**Files:**
- Modify: `frontend/index.html`（Task 2 代码之后追加）

- [ ] **Step 1：追加 `buildInnerPage()` 包装器函数**

```javascript
/**
 * 内页通用包装器：加页眉（深蓝+金线）+ 斜纹水印 + 页脚
 * @param {string} content  - 页面正文 HTML（不含页眉页脚）
 * @param {number} pageNum  - 当前页码（从1开始，封面不算）
 * @param {string} reportId
 */
function buildInnerPage(content, pageNum, reportId) {
  const rid = esc(reportId);
  return `<html><head><meta charset="UTF-8"><style>${PDF_STYLES}</style></head><body>
<div class="page inner-page" style="width:595px;min-height:842px;">
  <div class="diag-wm"></div>
  <div class="inner-header">
    <div class="logo-wrap">
      <div class="logo-icon">🎓</div>
      <span class="logo-text">AI高考志愿规划师 · 志愿规划报告书</span>
    </div>
    <span class="header-right">${rid}</span>
  </div>
  <div class="inner-body">
    ${content}
  </div>
  <div class="inner-footer">
    <span class="report-id">${rid}</span>
    <span class="wm">严禁倒卖</span>
    <span>第 ${pageNum} 页</span>
  </div>
</div>
</body></html>`;
}
```

- [ ] **Step 2：追加 `buildInfoPage()` 函数（第1页：考生信息 + 数据权威保障 + 警告）**

```javascript
/**
 * 第1页：考生信息 + 数据权威保障 + 严禁倒卖 + 报告结构说明
 */
function buildInfoPage(stu, reportId, ts) {
  const nickname = esc(stu.nickname || '考生');
  const province = esc(stu.province || '—');
  const score    = Number(stu.score) || '—';
  const rank     = esc(String(stu.rank || '估算中'));
  const subj     = esc(stu.subjectStr || stu.subject_str || '—');
  const obey     = stu.obey ? '✓ 服从' : '✗ 不服从';
  const economy  = esc(stu.economy || stu.family_economy || '—');
  const city     = esc((stu.cities || []).join(' / ') || '—');
  const rid      = esc(reportId);

  const content = `
    <div class="sec-title"><span>📋</span><span>考生信息</span><span class="sec-badge">STUDENT INFO</span></div>
    <div class="stu-card">
      <div class="stu-grid">
        <div class="stu-field"><label>报告编号</label><div class="val" style="font-family:monospace;font-size:11px;">${rid}</div></div>
        <div class="stu-field"><label>生成时间</label><div class="val" style="font-size:12px;">${esc(ts)}</div></div>
        <div class="stu-field"><label>考生昵称</label><div class="val">${nickname}</div></div>
        <div class="stu-field"><label>省份 / 分数</label><div class="val hi">${province} · ${score}分</div></div>
        <div class="stu-field"><label>省内位次（估算）</label><div class="val hi">${rank} 名</div></div>
        <div class="stu-field"><label>选科组合</label><div class="val" style="font-size:12px;">${subj}</div></div>
        <div class="stu-field"><label>服从调剂</label><div class="val" style="color:${stu.obey?'#16A34A':'#DC2626'};">${obey}</div></div>
        <div class="stu-field"><label>家庭经济</label><div class="val">${economy}</div></div>
        <div class="stu-field"><label>意向城市</label><div class="val">${city}</div></div>
      </div>
    </div>

    <div class="sec-title"><span>🛡️</span><span>数据权威性保障</span></div>
    <div class="auth-card">
      <div class="auth-item"><div class="auth-dot"></div><div><strong>权威数据来源：</strong>教育部阳光高考网 2021–2025 一分一段表，近6年2200万+真实录取记录，2000+高校覆盖34省</div></div>
      <div class="auth-item"><div class="auth-dot"></div><div><strong>精准排名定位：</strong>紧扣2026年最新"一分一段"分数排名，以省内位次为核心决策依据，规避年度波动风险</div></div>
      <div class="auth-item"><div class="auth-dot"></div><div><strong>AI推理引擎：</strong>Claude（Anthropic）· DeepSeek V4 Pro · GPT-5.5 三大顶尖模型交叉综合分析，多模型权重融合</div></div>
      <div class="auth-item"><div class="auth-dot"></div><div><strong>个性化匹配：</strong>深度结合考生兴趣爱好、性格特质、家庭背景、城市偏好，六维度加权综合推荐</div></div>
    </div>

    <div class="warn-banner">
      <span style="font-size:16px;">⚠️</span>
      <div>
        <div>严禁倒卖 · 本报告为考生 <strong>${nickname}</strong> 专属定制，违规转卖将触发系统告警及法律追责</div>
        <div style="font-weight:400;color:#B91C1C;margin-top:2px;font-size:10.5px;">报告编号 ${rid} 已与主播ID绑定，禁止转卖或二次传播</div>
      </div>
    </div>

    <div class="sec-title" style="margin-top:10px;"><span>📑</span><span>本报告结构</span></div>
    <div class="struct-grid">
      <div class="struct-item"><span class="lbl">板块一</span>封面基础信息（本页）</div>
      <div class="struct-item"><span class="lbl">板块二</span>核心定位分析</div>
      <div class="struct-item"><span class="lbl">板块三</span>分层院校明细（15所，18维度）</div>
      <div class="struct-item"><span class="lbl">板块四</span>AI个性化填报建议书</div>
      <div class="struct-item" style="background:#EFF6FF;border:1px solid #BFDBFE;"><span class="lbl" style="color:#2563EB;">附录</span>三档院校综合横向对比表</div>
      <div class="struct-item"><span class="lbl">板块五</span>免责声明</div>
    </div>`;

  return buildInnerPage(content, 1, reportId);
}
```

- [ ] **Step 3：浏览器验证**

Console 执行：
```javascript
renderPageToCanvas(buildInfoPage(S.student, 'GK-TEST-001', '2026年6月18日 11:39'))
  .then(c => { c.style.cssText='position:fixed;top:0;left:0;width:300px;z-index:9999;'; document.body.appendChild(c); });
```
预期：左上角出现白底内页，页眉深蓝+金线，考生信息卡蓝色左边框，数据权威卡黄色左边框，严禁倒卖红色横幅。

---

## Task 4：实现 `buildPositioningPage()`（第2页：核心定位分析）

**Files:**
- Modify: `frontend/index.html`（Task 3 之后追加）

- [ ] **Step 1：追加 `buildPositioningPage()` 函数**

```javascript
/**
 * 第2页：核心定位分析
 * data.tier_summary: { rush_count, stable_count, bottom_count, rush_prob_range, stable_prob_range, bottom_prob_range }
 * data.student_rank: 省内位次
 * data.positioning_text: （可选）AI生成的综合分析文字
 */
function buildPositioningPage(stu, data, reportId) {
  const ts  = data.tier_summary || {};
  const rank = esc(String(data.student_rank || stu.rank || '估算中'));
  const score = Number(stu.score) || '—';
  const province = esc(stu.province || '—');
  const rushCnt   = ts.rush_count   || (data.schools||[]).filter(s=>s.tier===0).length || 5;
  const stableCnt = ts.stable_count || (data.schools||[]).filter(s=>s.tier===1).length || 5;
  const safeCnt   = ts.bottom_count || (data.schools||[]).filter(s=>s.tier===2).length || 5;
  const posText   = esc(data.positioning_text || `您的高考分数 ${score} 分，省内位次约 ${rank} 名，结合意向城市与选科，系统为您筛选出最优志愿梯度组合。建议以"进好学校=进好专业"为原则，在稳妥院校中优先选择高就业率专业。`);
  const obeyNote  = stu.obey ? '您已选择服从调剂，有效降低滑档风险。建议在稳妥/保底院校优先勾选"服从专业调剂"，可提升录取概率约 8-12%。' : '您选择不服从调剂，请确保冲刺院校专业列表完整，避免因专业不服从导致退档。';

  const content = `
    <div class="sec-title"><span>📊</span><span>板块二：核心定位分析</span></div>
    <div class="pos-grid4">
      <div class="pos-card" style="border-top:3px solid #2563EB;">
        <div class="pc-label">高考分数</div>
        <div class="pc-val" style="color:#1E3A8A;font-size:20px;">${score}分</div>
        <div class="pc-sub">满分${stu.province==='上海'?660:750}分</div>
      </div>
      <div class="pos-card" style="border-top:3px solid #7C3AED;">
        <div class="pc-label">省内位次（估算）</div>
        <div class="pc-val" style="color:#7C3AED;font-size:15px;">${rank}</div>
        <div class="pc-sub">${province}物理类</div>
      </div>
      <div class="pos-card" style="border-top:3px solid #D97706;">
        <div class="pc-label">分数段定位</div>
        <div class="pc-val" style="color:#D97706;font-size:13px;">${esc(data.score_segment || '普通本科段')}</div>
        <div class="pc-sub">${esc(data.score_level || '中段考生')}</div>
      </div>
      <div class="pos-card" style="border-top:3px solid #16A34A;">
        <div class="pc-label">综合竞争力评级</div>
        <div class="pc-val" style="color:#16A34A;font-size:18px;">${esc(data.competition_grade || 'B')}</div>
        <div class="pc-sub">${esc(data.competition_desc || '全省中段')}</div>
      </div>
    </div>

    <div style="background:#F9FAFB;border:1px solid #E5E7EB;border-radius:6px;padding:12px 14px;margin-bottom:12px;font-size:11.5px;color:#374151;line-height:1.8;">
      <strong style="color:#1F2937;">综合分析：</strong>${posText}
    </div>

    <div class="sec-title"><span>🎯</span><span>院校分层规划（15所推荐）</span></div>
    <div class="tier-row">
      <div class="tier-blk rush">
        <div class="tier-lbl">🚀 冲刺院校</div>
        <div class="tier-cnt">${rushCnt} 所</div>
        <div class="tier-prob">录取概率 30%-60%</div>
      </div>
      <div class="tier-blk stable">
        <div class="tier-lbl">🎯 稳妥院校</div>
        <div class="tier-cnt">${stableCnt} 所</div>
        <div class="tier-prob">录取概率 60%-85%</div>
      </div>
      <div class="tier-blk safe">
        <div class="tier-lbl">🟢 保底院校</div>
        <div class="tier-cnt">${safeCnt} 所</div>
        <div class="tier-prob">录取概率 ≥85%</div>
      </div>
    </div>

    <div style="background:${stu.obey?'#F0FDF4':'#FFF7ED'};border:1px solid ${stu.obey?'#BBF7D0':'#FED7AA'};border-left:4px solid ${stu.obey?'#16A34A':'#D97706'};border-radius:4px;padding:10px 12px;margin-bottom:12px;font-size:11.5px;color:${stu.obey?'#166534':'#9A3412'};">
      <strong>${stu.obey?'✓ 服从调剂建议：':'⚠ 不服从调剂提示：'}</strong>${obeyNote}
    </div>

    <div style="background:#FFFBF0;border:1px solid #FDE68A;border-radius:6px;padding:10px 12px;font-size:11px;color:#374151;line-height:1.7;">
      <strong style="color:#D97706;">📐 概率算法说明（PRD v5.2 加权差值算法）：</strong><br>
      成绩排名推荐率 (rankProb) = 加权最低位次 − 学生省内位次 → 差值映射到6档离散概率（8% / 25% / 45% / 65% / 80% / 95%）<br>
      加权最低位次 = 2025年×0.5 + 2024年×0.3 + 2023年×0.2（3年数据齐全时）
    </div>`;

  return buildInnerPage(content, 2, reportId);
}
```

- [ ] **Step 2：浏览器验证**

Console 执行：
```javascript
renderPageToCanvas(buildPositioningPage(S.student, S.reportData, 'GK-TEST-001'))
  .then(c => { c.style.cssText='position:fixed;top:0;left:0;width:300px;z-index:9999;'; document.body.appendChild(c); });
```
预期：4格数据卡（蓝/紫/橙/绿上边框）+ 三色Tier分层块 + 黄色算法说明框。

---

## Task 5：实现 `buildSchoolCardHTML()`（单张学校卡片，18维度）

**Files:**
- Modify: `frontend/index.html`（Task 4 之后追加）

### 背景

此函数接收一个学校对象 `s`（来自 `data.schools` 数组）和 tier 标识，返回卡片 HTML 字符串（**不含页面包装**，由 Task 6 的分页函数组装）。

数据字段映射（与现有 `renderSchoolCard()` 相同）：
- `s.name`：学校名
- `s.tags`：`['985']` / `['211']` / `['双一流']` / 其他
- `s.tier`：`0`=冲刺，`1`=稳妥，`2`=保底
- `s.rank_prob`：主概率（rankProb，6档离散）
- `s.weighted_prob`：综合评分概率
- `s._intended_city`：`true` 表示来自意向城市（显示"●意向城市"标签）
- `s.city` / `s.province`：城市
- `s.admission_data.latest_min_score`：近年录取分
- `s.admission_data.trend_detail`：分数线趋势文字
- `s.dimensions.recommended_major`：推荐专业
- `s.dimensions.major_level`：专业地位
- `s.dimensions.tuition` / `s.dimensions.tuition_per_year`：学费
- `s.dimensions.tuition_total`：4年总费用
- `s.dimensions.employment_rate`：就业率
- `s.dimensions.employment_source`：就业数据来源
- `s.dimensions.avg_salary_start` / `s.dimensions.avg_salary`：应届起薪
- `s.dimensions.avg_salary_3yr`：3年后薪资
- `s.dimensions.core_positions`：核心岗位
- `s.dimensions.city_analysis`：城市分析（对象或字符串）
- `s.dimensions.ai_review`：AI点评（维度16）
- `s.dimensions.risk_analysis`：报考风险分析（维度17，可能缺失）
  - 结构：`{ score_diff: "高于/低于录取线X分", risk_level: "高/中/低", adjust_advice: "建议服从/谨慎/不建议" }`
- `s.dimensions.enroll_trend`：招生规模趋势（维度18，可能缺失）
  - 结构：`[ { year:2023, plan:120, actual:118 }, ... ]`，最多显示3年

- [ ] **Step 1：追加 `buildSchoolCardHTML()` 函数**

```javascript
/**
 * 单张学校卡片 HTML（含18维度，供 buildSchoolPages() 调用）
 * @param {object} s        - 学校数据对象
 * @param {number} idx      - 序号（从1开始）
 * @param {string} tierKey  - 'rush' | 'stable' | 'safe' | 'special'
 */
function buildSchoolCardHTML(s, idx, tierKey) {
  const dim  = s.dimensions || {};
  const adm  = s.admission_data || {};
  const prob = Math.round(s.rank_prob || s.weighted_prob || 0);
  const wProb= Math.round(s.weighted_prob || 0);
  const tc   = tierKey === 'rush' ? 'rush' : tierKey === 'stable' ? 'stable' : tierKey === 'safe' ? 'safe' : 'stable';

  // 标签
  const tags = s.tags || [];
  const badgeHtml =
    tags.includes('985') ? `<span class="badge b985">985</span>` :
    tags.includes('211') ? `<span class="badge b211">211</span>` :
    tags.includes('双一流') ? `<span class="badge bdf">双一流</span>` : '';
  const cityBadge = s._intended_city ? `<span class="badge bicy">● 意向城市</span>` : '';
  const pubBadge  = `<span class="badge bpub">公办</span>`;

  // 录取分
  const scoreText = adm.latest_min_score ? `${adm.latest_min_score}分` : '暂无数据';

  // 趋势
  const trendText = adm.trend_detail ? esc(adm.trend_detail) : '—';

  // 学费
  const tuitionVal = dim.tuition || dim.tuition_per_year || '';
  const rawTuition = parseInt(String(tuitionVal).replace(/[^0-9]/g,'')) || 0;
  const ecoBadge   = rawTuition > 0 && rawTuition <= 5000 ? `<span style="color:#16A34A;font-size:9.5px;"> 经济友好</span>` : '';
  const tuitionStr = tuitionVal ? `${esc(String(tuitionVal))}${ecoBadge}${dim.tuition_total ? ' · ' + esc(dim.tuition_total) : ''}` : '—';

  // 薪资
  const salStart = dim.avg_salary_start || dim.avg_salary || '';
  const sal3yr   = dim.avg_salary_3yr || '';
  const salStr   = salStart ? `${esc(String(salStart))}${sal3yr ? ' → ' + esc(String(sal3yr)) + '(3年后)' : ''}` : '—';

  // 城市分析
  let cityAnalysisStr = '—';
  if (dim.city_analysis && typeof dim.city_analysis === 'object') {
    const ca = dim.city_analysis;
    cityAnalysisStr = esc(ca.summary || [ca.location, ca.advantage, ca.job_market].filter(Boolean).join(' · ') || '—');
  } else if (dim.city_analysis) {
    cityAnalysisStr = esc(String(dim.city_analysis));
  }

  // 风险分析（维度17，可能缺失）
  let riskHtml = '';
  if (dim.risk_analysis) {
    const ra = dim.risk_analysis;
    const rlColor = ra.risk_level === '高' ? 'risk-high' : ra.risk_level === '中' ? 'risk-mid' : 'risk-low';
    riskHtml = `<div class="risk-box">
      <div class="risk-title">⚠️ 报考风险分析（维度17）</div>
      <div class="risk-grid">
        <div class="risk-item">分差：<span class="${rlColor}">${esc(ra.score_diff||'—')}</span></div>
        <div class="risk-item">风险：<span class="${rlColor}">${esc(ra.risk_level||'—')}</span></div>
        <div class="risk-item">调剂：<span>${esc(ra.adjust_advice||'—')}</span></div>
      </div>
    </div>`;
  }

  // 招生规模趋势（维度18，可能缺失）
  let enrollHtml = '';
  if (Array.isArray(dim.enroll_trend) && dim.enroll_trend.length > 0) {
    const rows = dim.enroll_trend.slice(-3).map(r => {
      const shrink = r.plan && r.actual && r.actual < r.plan ? '<span class="enroll-shrink">↓缩招</span>' : '—';
      return `<tr><td>${r.year||''}</td><td>${r.plan||'—'}</td><td>${r.actual||'—'}</td><td>${shrink}</td></tr>`;
    }).join('');
    enrollHtml = `<div class="enroll-box">
      <div class="enroll-lbl">📋 招生规模趋势（维度18）</div>
      <table class="enroll-table">
        <tr><th>年份</th><th>计划</th><th>实际</th><th>趋势</th></tr>
        ${rows}
      </table>
    </div>`;
  }

  // AI点评（维度16）
  const aiHtml = dim.ai_review
    ? `<div class="ai-cmt">💬 ${esc(dim.ai_review)}</div>` : '';

  return `<div class="school-card">
    <div class="sc-hd ${tc}">
      <div>
        <div class="sc-name">㊉${idx}. ${esc(s.name)}</div>
        <div class="sc-badges">${badgeHtml}${pubBadge}${cityBadge}</div>
      </div>
      <div class="prob-area">
        <div class="prob-big ${tc}">${prob}%</div>
        <div style="font-size:9.5px;color:#6B7280;text-align:right;">综合 ${wProb}%</div>
        <div class="prob-bar"><div class="prob-fill ${tc}" style="width:${Math.min(prob,100)}%"></div></div>
      </div>
    </div>
    <div class="sc-body">
      <div class="dim-grid">
        <div class="dim-item"><div class="dim-lbl">📍 城市</div><div class="dim-val">${esc(s.city||s.province||'—')}</div></div>
        <div class="dim-item"><div class="dim-lbl">📊 近年录取分（2025）</div><div class="dim-val mono">${scoreText}</div></div>
        <div class="dim-item"><div class="dim-lbl">📐 位次匹配</div><div class="dim-val">${esc(s.rank_match || (prob>=65?'✓ 位次匹配':'差距约X名'))}</div></div>
        <div class="dim-item"><div class="dim-lbl">📈 分数线趋势</div><div class="dim-val">${trendText}</div></div>
        <div class="dim-item"><div class="dim-lbl">🎓 推荐专业</div><div class="dim-val">${esc(dim.recommended_major||'—')}</div></div>
        <div class="dim-item"><div class="dim-lbl">💰 学费</div><div class="dim-val">${tuitionStr}</div></div>
        <div class="dim-item"><div class="dim-lbl">🏅 专业地位</div><div class="dim-val">${esc(dim.major_level||'—')}</div></div>
        <div class="dim-item"><div class="dim-lbl">💼 就业率</div><div class="dim-val">${esc(dim.employment_rate||'—')}${dim.employment_source?'<span style="font-size:9px;color:#9CA3AF;"> '+esc(dim.employment_source)+'</span>':''}</div></div>
        <div class="dim-item"><div class="dim-lbl">💵 平均薪资</div><div class="dim-val mono">${salStr}</div></div>
        <div class="dim-item"><div class="dim-lbl">🏢 主要岗位</div><div class="dim-val">${esc(dim.core_positions||'—')}</div></div>
        <div class="dim-item"><div class="dim-lbl">📡 5年趋势</div><div class="dim-val">${esc(dim.industry_trend||dim.five_year_trend||'—')}</div></div>
        <div class="dim-item"><div class="dim-lbl">🌆 城市分析</div><div class="dim-val">${cityAnalysisStr}</div></div>
      </div>
      ${riskHtml}
      ${enrollHtml}
      ${aiHtml}
    </div>
  </div>`;
}
```

- [ ] **Step 2：浏览器验证**

```javascript
// 取第一所学校测试
const s0 = S.reportData.schools[0];
const cardHtml = buildSchoolCardHTML(s0, 1, s0.tier===0?'rush':s0.tier===1?'stable':'safe');
renderPageToCanvas(buildInnerPage(cardHtml, 3, 'GK-TEST'))
  .then(c => { c.style.cssText='position:fixed;top:0;left:0;width:300px;z-index:9999;'; document.body.appendChild(c); });
```
预期：出现学校卡片，卡片头部颜色与tier对应（冲刺=红，稳妥=蓝，保底=绿），概率数字正确，各维度数据可见。

---

## Task 6：实现 `buildSchoolPages()`（自动分页的学校卡片组）

**Files:**
- Modify: `frontend/index.html`（Task 5 之后追加）

### 背景

此函数返回一个 HTML 字符串数组，每项为一整页内容（已包装完整内页格式）。

分页策略：
- 每页可用高度约 **760px**（842 - 页眉55 - 页脚35 - 内边距各18）
- 每张学校卡片的**估算高度**：基础 220px + 每有 riskHtml 加 60px + 每有 enrollHtml 加 80px + 每有 aiHtml 加 50px
- 累积高度超过 740px 时，当前页截止，开启新页
- 特别关注区（意向学校）固定放在学校页第一页的顶部，高度按学校数量估算

- [ ] **Step 1：追加 `buildSchoolPages()` 函数**

```javascript
/**
 * 返回学校卡片页 HTML 字符串数组（每项为一完整内页）
 * 起始页码从 pageStart 开始（调用方传入，通常是3）
 */
function buildSchoolPages(stu, data, reportId, pageStart) {
  const schools  = data.schools || [];
  const specials = schools.filter(s => s._is_intended);   // 特别关注区（意向学校）
  const rush     = schools.filter(s => s.tier === 0 && !s._is_intended);
  const stable   = schools.filter(s => s.tier === 1 && !s._is_intended);
  const safe     = schools.filter(s => s.tier === 2 && !s._is_intended);

  const pages = [];
  let pageNum = pageStart;
  let currentBlocks = [];   // 当前页的 HTML 片段数组
  let currentHeight = 0;
  const MAX_H = 740;

  function estimateCardHeight(s) {
    const dim = s.dimensions || {};
    let h = 220;
    if (dim.risk_analysis) h += 60;
    if (Array.isArray(dim.enroll_trend) && dim.enroll_trend.length) h += 80;
    if (dim.ai_review) h += 50;
    return h;
  }

  function flushPage() {
    if (currentBlocks.length === 0) return;
    pages.push(buildInnerPage(currentBlocks.join(''), pageNum++, reportId));
    currentBlocks = [];
    currentHeight = 0;
  }

  function addBlock(html, estHeight) {
    if (currentHeight + estHeight > MAX_H && currentBlocks.length > 0) {
      flushPage();
    }
    currentBlocks.push(html);
    currentHeight += estHeight;
  }

  // 特别关注区
  if (specials.length > 0) {
    const specialRows = specials.map(s => {
      const prob = Math.round(s.rank_prob || 0);
      const tc = prob >= 85 ? 'bsafe' : prob >= 60 ? 'bs' : 'br';
      const tags = s.tags || [];
      const badge = tags.includes('985') ? `<span class="badge b985">985</span>` :
                    tags.includes('211') ? `<span class="badge b211">211</span>` :
                    tags.includes('双一流') ? `<span class="badge bdf">双一流</span>` : '';
      return `<div class="sp-row">
        <div style="display:flex;align-items:center;gap:6px;">
          <span style="font-size:13px;font-weight:600;color:#1F2937;">${esc(s.name)}</span>
          ${badge}
          <span style="font-size:10px;color:#D97706;">★ 意向</span>
        </div>
        <div style="display:flex;align-items:center;gap:6px;">
          <span class="prob-big ${tc === 'bsafe' ? 'safe' : tc === 'bs' ? 'stable' : 'rush'}" style="font-size:18px;">${prob}%</span>
          <span class="badge ${tc}">${prob>=85?'保底':prob>=60?'稳妥':'冲刺'}</span>
        </div>
      </div>`;
    }).join('');
    const specialHtml = `
      <div class="sec-title"><span>📌</span><span>特别关注区（意向学校）</span><span style="font-size:10px;color:#9CA3AF;font-weight:400;margin-left:auto;">不计入15所推荐总数</span></div>
      <div class="special-zone">
        <div style="font-size:10.5px;color:#92400E;margin-bottom:8px;">★ 以下为您填写的意向学校，无论概率高低均完整展示。</div>
        ${specialRows}
      </div>`;
    addBlock(specialHtml, 60 + specials.length * 48);
  }

  // 冲刺院校
  if (rush.length > 0) {
    addBlock(`<div class="sec-title" style="background:#FEF2F2;border-radius:5px;padding:6px 10px;color:#DC2626;border-bottom:none;margin-bottom:10px;">🚀 冲刺院校（${rush.length}所）· 录取概率 30%-60%</div>`, 36);
    rush.forEach((s, i) => addBlock(buildSchoolCardHTML(s, i+1, 'rush'), estimateCardHeight(s)));
  }

  // 稳妥院校
  if (stable.length > 0) {
    addBlock(`<div class="sec-title" style="background:#EFF6FF;border-radius:5px;padding:6px 10px;color:#2563EB;border-bottom:none;margin-bottom:10px;">🎯 稳妥院校（${stable.length}所）· 录取概率 60%-85%</div>`, 36);
    stable.forEach((s, i) => addBlock(buildSchoolCardHTML(s, rush.length+i+1, 'stable'), estimateCardHeight(s)));
  }

  // 保底院校
  if (safe.length > 0) {
    addBlock(`<div class="sec-title" style="background:#F0FDF4;border-radius:5px;padding:6px 10px;color:#16A34A;border-bottom:none;margin-bottom:10px;">🟢 保底院校（${safe.length}所）· 录取概率 ≥85%</div>`, 36);
    safe.forEach((s, i) => addBlock(buildSchoolCardHTML(s, rush.length+stable.length+i+1, 'safe'), estimateCardHeight(s)));
  }

  flushPage();
  return pages;
}
```

- [ ] **Step 2：浏览器验证**

```javascript
const pages = buildSchoolPages(S.student, S.reportData, 'GK-TEST', 3);
console.log('学校页数:', pages.length);
// 渲染第一页看效果
renderPageToCanvas(pages[0])
  .then(c => { c.style.cssText='position:fixed;top:0;left:0;width:300px;z-index:9999;'; document.body.appendChild(c); });
```
预期：Console 输出学校页数（应为5-12之间），左上角出现第一张学校卡片页。

---

## Task 7：实现 `buildComparisonPage()`、`buildSuggestionsPage()`、`buildDisclaimerPage()`

**Files:**
- Modify: `frontend/index.html`（Task 6 之后追加）

- [ ] **Step 1：追加 `buildComparisonPage()` 函数**

```javascript
/**
 * 三档横向对比表页
 */
function buildComparisonPage(data, reportId, pageNum) {
  const schools = data.schools || [];
  const rush   = schools.filter(s => s.tier === 0 && !s._is_intended);
  const stable = schools.filter(s => s.tier === 1 && !s._is_intended);
  const safe   = schools.filter(s => s.tier === 2 && !s._is_intended);

  function schoolRow(s, tierCls) {
    const dim = s.dimensions || {};
    const adm = s.admission_data || {};
    const prob = Math.round(s.rank_prob || s.weighted_prob || 0);
    const tags = s.tags || [];
    const tierLabel = tierCls==='rush'?'冲刺':tierCls==='stable'?'稳妥':'保底';
    const badge = tags.includes('985')?'985':tags.includes('211')?'211':tags.includes('双一流')?'双一流':'公办';
    const scoreText = adm.latest_min_score || '—';
    const employ = dim.employment_rate || '—';
    const salary = dim.avg_salary_start || dim.avg_salary || '—';
    const tuition = dim.tuition || dim.tuition_per_year || '—';
    const risk = dim.risk_analysis ? (dim.risk_analysis.risk_level||'—') : '—';
    const riskCls = risk==='高'?'cmp-rush':risk==='低'?'cmp-safe':risk==='中'?'cmp-stable':'';
    return `<tr>
      <td class="cmp-name">${esc(s.name)}${s._is_intended?'★':''}</td>
      <td>${badge}</td>
      <td class="mono">${scoreText}</td>
      <td class="${'cmp-'+tierCls}">${prob}%</td>
      <td>${esc(String(employ))}</td>
      <td class="mono">${esc(String(salary))}</td>
      <td>${esc(String(tuition))}</td>
      <td class="${riskCls}">${risk}</td>
    </tr>`;
  }

  const content = `
    <div class="sec-title"><span>📊</span><span>三档院校综合横向对比表</span></div>
    <div style="font-size:11px;color:#6B7280;margin-bottom:10px;">数据来源与各院校分析卡片保持一致，按冲刺/稳妥/保底分组展示</div>
    <table class="cmp-table">
      <thead>
        <tr><th>院校名称</th><th>层次</th><th>近年录取分</th><th>录取概率</th><th>就业率</th><th>均薪（月）</th><th>年学费</th><th>风险</th></tr>
      </thead>
      <tbody>
        <tr class="cmp-group"><td colspan="8">🚀 冲刺院校（${rush.length}所）</td></tr>
        ${rush.map(s=>schoolRow(s,'rush')).join('')}
        <tr class="cmp-group"><td colspan="8">🎯 稳妥院校（${stable.length}所）</td></tr>
        ${stable.map(s=>schoolRow(s,'stable')).join('')}
        <tr class="cmp-group"><td colspan="8">🟢 保底院校（${safe.length}所）</td></tr>
        ${safe.map(s=>schoolRow(s,'safe')).join('')}
      </tbody>
    </table>
    <div style="font-size:10px;color:#9CA3AF;line-height:1.7;">
      * 就业率数据来源：教育部就业质量报告（各校官方）· 薪资数据来源：麦可思2025届调查 · 录取分以2025年该省最低分为准
    </div>`;

  return buildInnerPage(content, pageNum, reportId);
}
```

- [ ] **Step 2：追加 `buildSuggestionsPage()` 函数**

```javascript
/**
 * AI个性化填报建议书页（板块四）
 * data.suggestion: 后端返回的AI建议文本（可能是字符串或结构化对象）
 */
function buildSuggestionsPage(data, stu, reportId, pageNum) {
  // 尝试解析后端建议，兼容字符串和对象
  const sug = data.suggestion || data.ai_suggestion || {};
  const getStr = (key, fallback) => {
    if (typeof sug === 'string') return key === 'overall' ? sug : fallback;
    return esc(String(sug[key] || fallback));
  };

  const score    = Number(stu.score) || '—';
  const rank     = esc(String(stu.rank || '估算中'));
  const province = esc(stu.province || '—');
  const majors   = ((stu.majors||[]).length ? stu.majors : (data.pref_majors||[])).join('、') || '综合类';
  const personality = (stu.personality || stu.personalities || []).join('、') || '未填写';

  const schools = data.schools || [];
  const rush   = schools.filter(s=>s.tier===0&&!s._is_intended).map(s=>esc(s.name));
  const stable = schools.filter(s=>s.tier===1&&!s._is_intended).map(s=>esc(s.name));
  const safe   = schools.filter(s=>s.tier===2&&!s._is_intended).map(s=>esc(s.name));

  const content = `
    <div class="sec-title"><span>🤖</span><span>板块四：AI 个性化填报建议书</span><span class="sec-badge" style="background:#7C3AED;">DeepSeek × Claude × GPT</span></div>

    <div class="sug-sec">
      <div class="sug-title">一、成绩定位 & 竞争分析</div>
      <div class="sug-text">${getStr('positioning', `您的高考分数 ${score} 分，省内位次约 ${rank} 名，处于${province}省中分段。建议在稳妥院校中优先选择计算机、软件工程等高就业率专业，以"进好学校=进好专业"为原则。`)}</div>
    </div>

    <div class="sug-sec">
      <div class="sug-title">二、志愿梯度填报策略</div>
      <div class="sug-item"><div class="sug-num">1</div><div>冲刺志愿（${rush.length}所）分数线要有5-15分梯度，不要押注单一院校，建议优先选：${rush.slice(0,3).join('、')||'见推荐列表'}</div></div>
      <div class="sug-item"><div class="sug-num">2</div><div>稳妥志愿（${stable.length}所）确保每所都是真实愿意就读，推荐重点关注：${stable.slice(0,3).join('、')||'见推荐列表'}</div></div>
      <div class="sug-item"><div class="sug-num">3</div><div>保底志愿（${safe.length}所）务必保留至少2所分差在40分以上的院校：${safe.slice(-2).join('、')||'见推荐列表'}</div></div>
      <div class="sug-item"><div class="sug-num">4</div><div>同一学校多专业志愿跨度不超过15分，防止调剂到不喜欢的方向</div></div>
    </div>

    <div class="sug-sec">
      <div class="sug-title">三、性格特质 × 专业建议</div>
      <div class="sug-text">${getStr('personality_advice', `您的性格标签为"${personality}"，结合选科组合，高度适配计算机/软件工程/自动化/电气工程方向。逻辑分析型考生在理工专业中有天然学习优势，且这些专业的就业薪资增长曲线最为陡峭（3年翻番率高）。`)}</div>
    </div>

    <div class="sug-sec">
      <div class="sug-title">四、调剂风险提示 & 家庭经济适配</div>
      <div class="sug-text">${getStr('adjust_advice', `${stu.obey?'服从调剂是明智之举，但服从调剂≠接受任何专业。建议在每所学校优先排列可接受的专业，服从调剂仅作最后保障。':'您选择不服从调剂，请确保志愿专业列表完整，避免因不服从导致退档风险。'}`)}</div>
    </div>

    <div class="sug-sec">
      <div class="sug-title">五、四大填报核心原则</div>
      <div class="sug-item"><div class="sug-num">1</div><div><strong>冲刺要有梯度：</strong>5所冲刺院校分数线有5-15分梯度，不集中于同一分数线</div></div>
      <div class="sug-item"><div class="sug-num">2</div><div><strong>稳妥不能凑数：</strong>每所稳妥院校必须是你真正愿意就读的，不要以"保底心态"填入</div></div>
      <div class="sug-item"><div class="sug-num">3</div><div><strong>保底要真保底：</strong>分差低于30分不算保底，至少保留2所分差40分+的院校</div></div>
      <div class="sug-item"><div class="sug-num">4</div><div><strong>以官为准：</strong>AI推荐仅供参考，最终以官方志愿系统投档线为准</div></div>
    </div>

    <div class="grad-box">
      <div class="grad-title">📋 整体梯度搭配策略总结</div>
      <div class="grad-row"><span class="gb-r">🚀 冲刺</span><span>建议冲刺2-3所：${rush.slice(0,3).join(' + ')||'见推荐列表'}（核心目标）</span></div>
      <div class="grad-row"><span class="gb-s">🎯 稳妥</span><span>建议稳妥3-5所：${stable.slice(0,5).join(' · ')||'见推荐列表'}</span></div>
      <div class="grad-row"><span class="gb-b">🟢 保底</span><span>保底务必保留：${safe.slice(-3).join(' · ')||'见推荐列表'}（分差最安全）</span></div>
      <div style="margin-top:8px;font-size:10.5px;color:#6B7280;line-height:1.6;">
        ⚠️ 冲刺志愿建议勾选"服从专业调剂"，降低因专业不足而退档的风险。
      </div>
    </div>`;

  return buildInnerPage(content, pageNum, reportId);
}
```

- [ ] **Step 3：追加 `buildDisclaimerPage()` 函数**

```javascript
/**
 * 免责声明页（板块五，最后一页）
 */
function buildDisclaimerPage(stu, reportId, ts, qrDataUrl, pageNum) {
  const rid      = esc(reportId);
  const nickname = esc(stu.nickname || '考生');
  const qrImg    = qrDataUrl
    ? `<img src="${qrDataUrl}" style="width:56px;height:56px;display:block;border-radius:3px;">`
    : `<div style="width:56px;height:56px;background:#D0D8E8;border-radius:3px;"></div>`;

  const content = `
    <div class="sec-title"><span>📜</span><span>板块五：免责声明</span></div>

    <div class="disc-card">
      <div class="disc-title">数据来源说明</div>
      本报告数据来源于：教育部阳光高考网官方数据（2020-2025年）、各省级教育考试院公开发布的一分一段表、
      教育部2024-2025年就业质量报告、麦可思研究院应届生薪资调查（2025届）、
      各高校官方招生简章及招生计划公告。数据截止2026年6月，如高校有临时政策调整，以官方最新公告为准。
    </div>

    <div class="disc-card">
      <div class="disc-title">AI模型说明</div>
      本报告分析部分由 Claude（Anthropic）、DeepSeek V4 Pro、GPT-5.5 三大语言模型交叉综合生成，
      模型输出已经过人工规则引擎过滤和置信度校验。AI 模型负责解释与建议，
      录取概率计算基于历史数据统计模型，不依赖 AI 推测。
    </div>

    <div class="disc-card">
      <div class="disc-title">免责说明</div>
      本报告所有分析结果<strong>仅供参考，不构成正式志愿填报建议</strong>。高考志愿填报受多种因素影响，
      包括但不限于：2026年实际录取政策调整、院校临时变更招生计划、考生现场发挥及排名波动。
      最终志愿填报决策请考生本人、家长及专业升学顾问综合判断后决定。
      本平台不对因参考本报告造成的任何损失承担法律责任。
    </div>

    <div class="warn-banner" style="margin-top:14px;">
      <span style="font-size:18px;">⚠️</span>
      <div>
        <div>严禁倒卖 · 本报告为考生 <strong>${nickname}</strong> 专属定制</div>
        <div style="font-weight:400;color:#B91C1C;margin-top:2px;font-size:10.5px;">
          报告编号：${rid} · 主播ID已绑定 · 违规转卖将触发系统告警及法律追责
        </div>
      </div>
    </div>

    <div style="margin-top:20px;text-align:center;">
      <div style="font-size:11px;color:#9CA3AF;line-height:1.8;">
        <div>© 2026 AI高考志愿规划师 · lumenaistudio.co</div>
        <div>报告编号：${rid} · 生成时间：${esc(ts)}</div>
        <div>数据库：2000+高校 · 34省 · 6年 · 2200万+录取记录</div>
      </div>
      <div style="display:flex;justify-content:center;gap:20px;margin-top:14px;align-items:center;">
        <div>
          <div style="width:60px;height:60px;background:white;border:1px solid #E5E7EB;border-radius:4px;padding:3px;">${qrImg}</div>
          <div style="font-size:9px;color:#9CA3AF;text-align:center;margin-top:4px;">扫码验真伪</div>
        </div>
        <div style="font-size:10px;color:#6B7280;line-height:1.7;text-align:left;">
          <div>🔍 扫描二维码可验证报告真伪</div>
          <div>📱 微信小程序"分数分析师"</div>
          <div>🌐 AI高考志愿规划师 · 专业护航高考</div>
        </div>
      </div>
    </div>`;

  return buildInnerPage(content, pageNum, reportId);
}
```

- [ ] **Step 4：浏览器验证对比表页**

```javascript
renderPageToCanvas(buildComparisonPage(S.reportData, 'GK-TEST', 99))
  .then(c => { c.style.cssText='position:fixed;top:0;left:0;width:300px;z-index:9999;'; document.body.appendChild(c); });
```
预期：出现深蓝色表头、按冲/稳/保分组的对比表格。

---

## Task 8：替换 `downloadPDF()` 主控函数 + 删除旧函数

**Files:**
- Modify: `frontend/index.html:1610–1910`

### 删除以下旧函数（全部）

- **第1610–1654行**：`extractTextBlocks()` 函数——全部删除
- **第1655–1845行**：`downloadPDF()` 旧函数体——全部替换为下面的新版本
- **第1863–1910行**：`buildCoverHTML()` 函数——全部删除

`addDiagonalWatermarks()`（第1847–1861行）**保留不动**。

- [ ] **Step 1：删除 `extractTextBlocks()`（第1610–1654行）**

直接删除这45行。

- [ ] **Step 2：删除 `buildCoverHTML()`（第1863–1910行）**

直接删除这48行。

- [ ] **Step 3：将第1655–1845行的 `downloadPDF()` 替换为新版**

```javascript
async function downloadPDF() {
  if (!window.jspdf || !window.html2canvas) {
    showToast('PDF库加载中，请稍候重试', 'warning'); return;
  }
  const reportEl = document.getElementById('reportContent');
  if (!reportEl || !reportEl.innerHTML.trim()) {
    showToast('请先生成报告', 'warning'); return;
  }

  const stu  = S.student || {};
  const data = S.reportData || {};
  const rawId = (data._orderId || S.orderId || '').replace(/[^A-Za-z0-9\-]/g, '');
  const reportId = rawId && rawId !== '-'
    ? rawId
    : 'GK' + new Date().toISOString().replace(/[-T:.Z]/g,'').slice(2,14)
      + '-' + Math.random().toString(36).slice(2,6).toUpperCase();

  const now    = new Date();
  const ts     = now.getFullYear() + '年' + (now.getMonth()+1) + '月' + now.getDate() + '日 '
               + String(now.getHours()).padStart(2,'0') + ':' + String(now.getMinutes()).padStart(2,'0');
  const name   = esc(stu.nickname || '考生');

  // 生成 QR code DataURL
  let qrDataUrl = null;
  if (window.QRCode) {
    try {
      const tmpDiv = document.createElement('div');
      tmpDiv.style.cssText = 'position:fixed;top:-9999px;left:-9999px;';
      document.body.appendChild(tmpDiv);
      new QRCode(tmpDiv, {
        text: reportId.substring(0, 20),
        width: 80, height: 80,
        colorDark: '#091630', colorLight: '#FFFFFF',
        correctLevel: QRCode.CorrectLevel.L
      });
      await new Promise(r => setTimeout(r, 250));
      const qrCanvas = tmpDiv.querySelector('canvas');
      if (qrCanvas) qrDataUrl = qrCanvas.toDataURL('image/png');
      document.body.removeChild(tmpDiv);
    } catch(e) {
      console.warn('QR 生成失败:', e.message);
    }
  }

  // 组装所有页面
  const allPages = [];
  allPages.push(buildCoverPage(stu, reportId, qrDataUrl, ts));           // 封面
  allPages.push(buildInfoPage(stu, reportId, ts));                        // 第1页
  allPages.push(buildPositioningPage(stu, data, reportId));               // 第2页

  const schoolPages = buildSchoolPages(stu, data, reportId, 3);          // 第3页起
  allPages.push(...schoolPages);

  const cmpPageNum  = allPages.length;                                    // 对比表页
  allPages.push(buildComparisonPage(data, reportId, cmpPageNum));

  const sugPageNum  = allPages.length + 1;
  allPages.push(buildSuggestionsPage(data, stu, reportId, sugPageNum));   // 建议书页

  const discPageNum = allPages.length + 1;
  allPages.push(buildDisclaimerPage(stu, reportId, ts, qrDataUrl, discPageNum)); // 免责页

  const totalPages = allPages.length;
  showToast(`PDF生成中，共 ${totalPages} 页，请稍候…`, 'info');

  try {
    const { jsPDF } = window.jspdf;
    const pdf = new jsPDF({ orientation: 'portrait', unit: 'mm', format: 'a4' });
    const PW  = pdf.internal.pageSize.getWidth();   // 210mm
    const PH  = pdf.internal.pageSize.getHeight();  // 297mm

    for (let i = 0; i < allPages.length; i++) {
      showToast(`PDF生成中 ${i+1}/${totalPages} 页…`, 'info');
      const canvas = await renderPageToCanvas(allPages[i]);
      const imgData = canvas.toDataURL('image/jpeg', 0.92);
      const imgH    = (canvas.height * PW) / canvas.width;

      if (i > 0) pdf.addPage();
      pdf.addImage(imgData, 'JPEG', 0, 0, PW, Math.min(imgH, PH));

      // 斜纹水印叠加（用旧函数）
      addDiagonalWatermarks(pdf, PW, PH, ts, reportId);
    }

    pdf.save(`志愿报告_${name}_${reportId}.pdf`);
    showToast(`✓ PDF下载成功，共 ${totalPages} 页`, 'success');
  } catch(e) {
    showToast('PDF生成失败：' + e.message, 'error');
    console.error('PDF error:', e);
  }
}
```

- [ ] **Step 4：浏览器冒烟测试**

1. 生成一份完整报告（填表 → 解锁）
2. 点击"📥 下载PDF"
3. 观察：
   - Toast 显示"PDF生成中 1/N页"并逐步更新
   - 约20-40秒后弹出下载
   - 下载文件命名格式正确：`志愿报告_昵称_GKxxx.pdf`

- [ ] **Step 5：对照验收**

打开下载的 PDF，与浏览器中 `docs/pdf_preview.html` 并排对比：
- [ ] 封面：深蓝金色，建筑插图可见，QR码有内容，报告编号正确
- [ ] 第1页：考生信息卡（蓝色左边框）、数据权威卡（黄色左边框）、红色警告横幅
- [ ] 第2页：4格定位卡、三色Tier分层块、黄色算法说明
- [ ] 学校页：卡片头部颜色按tier区分，概率数字正确，维度数据可见
- [ ] 对比表：深蓝表头、分组行加粗、tier颜色标注正确
- [ ] 建议书：6节内容、梯度搭配策略蓝色总结框
- [ ] 免责页：三张卡片、红色警告横幅、QR码、版权信息

---

## Task 9：边界情况处理 + 最终提交

**Files:**
- Modify: `frontend/index.html`（在各函数内补充 fallback）

- [ ] **Step 1：处理 `data.schools` 为空的情况**

在 `downloadPDF()` 中，`allPages.push(...schoolPages)` 之前加：
```javascript
if ((data.schools || []).length === 0) {
  allPages.push(buildInnerPage(
    '<div style="text-align:center;padding:40px;color:#9CA3AF;font-size:14px;">暂无推荐院校数据</div>',
    3, reportId
  ));
}
```

- [ ] **Step 2：处理 `data.suggestion` 不存在时建议书的回退**

`buildSuggestionsPage()` 已使用 `getStr(key, fallback)` 兼容，无需额外修改。

- [ ] **Step 3：Chrome 控制台无 Error 检查**

生成PDF过程中，打开DevTools Console，确认：
- 无红色 Error 输出
- 无 `html2canvas` 跨域警告（如有，在 `renderPageToCanvas` 里已设置 `useCORS:true`）

- [ ] **Step 4：git commit**

```bash
cd /d/dev/NewGKAi
git add frontend/index.html
git commit -m "feat: PDF报告重设计 — 方案A全HTML渲染，深蓝金色封面+7页A4报告

- 新增 PDF_STYLES CSS常量（从pdf_preview.html提取）
- 新增 renderPageToCanvas() 统一截图辅助函数
- 新增 buildCoverPage() 深蓝金色封面含SVG建筑+QR码
- 新增 buildInnerPage() 内页通用页眉页脚包装器
- 新增 buildInfoPage() 考生信息+数据权威+警告第1页
- 新增 buildPositioningPage() 核心定位分析第2页
- 新增 buildSchoolCardHTML() 18维度学校卡片
- 新增 buildSchoolPages() 自动分页学校卡片组
- 新增 buildComparisonPage() 三档横向对比表
- 新增 buildSuggestionsPage() AI个性化建议书（7节）
- 新增 buildDisclaimerPage() 免责声明+QR验真伪
- 重写 downloadPDF() 主控函数，进度Toast逐页更新
- 删除 extractTextBlocks()、旧downloadPDF()、buildCoverHTML()
视觉标准：docs/pdf_preview.html"
```

---

## 自检清单（开发提交前必过）

| 检查项 | 通过标准 |
|--------|---------|
| 封面风格 | 与 `pdf_preview.html` 封面肉眼一致（深蓝底/金色弧线/建筑图） |
| 内页页眉 | 深蓝背景 + 3px金色下边线 + 报告编号 |
| 斜纹水印 | 每页可见淡金色斜纹（不遮挡内容） |
| 学校卡片 | 头部颜色正确（冲刺红/稳妥蓝/保底绿）|
| 维度17 | 有数据时显示报考风险框，无数据时不显示空框 |
| 维度18 | 有数据时显示招生规模表，无数据时不显示空表 |
| 对比表 | 深蓝表头，15所学校全部出现 |
| 建议书 | 梯度搭配总结框学校名称来自真实数据 |
| PDF文件名 | `志愿报告_昵称_GKxxxxx.pdf` |
| 无 JS Error | Chrome DevTools Console 无红色错误 |
