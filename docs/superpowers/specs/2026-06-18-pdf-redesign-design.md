# PDF报告重设计规格 — 方案A（全HTML渲染）

**日期：** 2026-06-18  
**状态：** 已用户确认  
**参考视觉：** `docs/pdf_preview.html`（以此为最终效果标准）  
**修改文件：** `frontend/index.html`

---

## 1. 目标

把"下载PDF"功能生成的报告，从现有的简单白底封面+jsPDF文字内页，完整替换成与 `pdf_preview.html` 视觉一致的深蓝金色多页A4报告。

---

## 2. 技术方案

**方案A：全HTML渲染 → html2canvas → jsPDF**

```
buildAllPDFPages(data)
  → 向 #pdfRenderZone 写入每页 HTML（595×842px）
  → html2canvas(zone, {scale:3}) 截图
  → pdf.addImage(canvas, 'PNG', 0, 0, 210, 297)
  → pdf.addPage() → 循环至所有页完成
  → pdf.save(文件名)
```

---

## 3. 页面结构

| 页 | 内容 | 构建函数 |
|----|------|---------|
| 封面 | 深蓝金色背景 + SVG建筑插图 + Logo + QR码 | `buildCoverPage()` |
| 第1页 | 考生信息卡 + 数据权威保障 + 严禁倒卖横幅 + 报告结构说明 | `buildInfoPage()` |
| 第2页 | 核心定位分析：4格数据卡 + Tier分层 + 调剂提示 + 算法说明 | `buildPositioningPage()` |
| 第3-N页 | 📌特别关注区 + 冲刺/稳妥/保底学校卡片（18维度，约1-2所/页） | `buildSchoolPages()` |
| N+1页 | 三档横向对比表（15所×8列） | `buildComparisonPage()` |
| N+2页 | AI个性化建议书（7节 + 梯度搭配策略总结） | `buildSuggestionsPage()` |
| 最后页 | 免责声明 + 防伪QR码 | `buildDisclaimerPage()` |

---

## 4. 样式规范

直接沿用 `pdf_preview.html` 的 CSS，抽离为 JS 字符串常量 `PDF_STYLES`，注入每页的 `<style>` 标签，不影响主页面样式。

**配色（与 pdf_preview.html 一致）：**
- 封面背景：`#091630`
- 金色装饰：`#C9A84C`
- 内页页眉背景：`#091630` + 底部 3px 金色线
- 内页白底：`#FFFFFF`
- 斜纹水印：`rgba(200,168,72,0.025)`

---

## 5. 分页逻辑

学校卡片高度不固定（数据多少决定高度）。处理方式：

1. 每页维护剩余高度计数器（可用高度 = 842 - 页眉45 - 页脚35 = **762px**）
2. 每张卡片渲染前估算高度（约 380-450px）
3. 剩余高度不足时 → 当前页截图 → 新建空白页 → 继续
4. 特别关注区（意向学校）固定在学校卡片段的第一页顶部

---

## 6. 生成进度提示

```
Toast: "PDF生成中 1/N页…"  → 每页更新
Toast: "✓ PDF已生成，共N页" → 完成
```

---

## 7. 函数清单

| 函数 | 说明 |
|------|------|
| `downloadPDF()` | 入口，替换现有实现 |
| `buildCoverPage(stu, reportId, qrDataUrl, ts)` | 封面HTML字符串 |
| `buildInfoPage(stu, reportId, ts)` | 第1页HTML |
| `buildPositioningPage(stu, data)` | 第2页HTML |
| `buildSchoolPages(stu, data)` | 返回学校页HTML数组（已分好页） |
| `buildSchoolCardHTML(school, idx, tier)` | 单张学校卡片（18维度）HTML |
| `buildComparisonPage(data)` | 对比表HTML |
| `buildSuggestionsPage(data, stu)` | AI建议HTML |
| `buildDisclaimerPage(stu, reportId, ts, qrDataUrl)` | 免责HTML |
| `buildInnerPageWrapper(content, pageNum, reportId)` | 内页页眉页脚包装器 |
| `renderPageToCanvas(html)` | 注入#pdfRenderZone → html2canvas → 返回canvas |

---

## 8. 改动范围

- **删除：** 现有 `buildCoverHTML()` 函数（约47行）
- **删除：** 现有 `downloadPDF()` 函数内的旧逻辑（约230行）
- **新增：** 上述10个函数（约600-800行）
- **新增：** `PDF_STYLES` CSS 常量（从pdf_preview.html提取）
- **不变：** 其余所有页面逻辑、API调用、表单逻辑

---

## 9. 验收标准

下载的PDF与 `docs/pdf_preview.html` 在浏览器中的视觉效果一致，包括：
- 封面深蓝金色风格 + SVG建筑
- 内页页眉（深蓝背景+金色线）+ 斜纹水印
- 学校卡片18维度全量展示
- 三档横向对比表
- AI建议书7节
- 免责声明 + QR码
