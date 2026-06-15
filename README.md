# HotRadar — 国内热点监控

抓取 **微博热搜榜**、**知乎热榜**、**抖音总榜** 每日热点，输出到 SMCC 原料库并发送飞书群通知。

## 数据来源

通过 [tophub.today](https://tophub.today) 聚合平台获取数据，一次浏览器渲染抓取全部 3 个平台。

**为什么选 tophub.today？**
- 免去逐个平台处理反爬的麻烦
- 数据格式统一（标题 + 热度值）
- 包含微博/知乎/抖音三大平台

## 快速开始

```bash
# 安装依赖
pip install -r requirements.txt

# 安装 Playwright 浏览器引擎（首次使用）
python -m playwright install chromium

# 抓取全部平台
python main.py
```

## 使用指南

### CLI 参数

| 参数 | 简写 | 说明 | 默认值 |
|------|------|------|--------|
| `--platform` | `-p` | 平台列表，逗号分隔 | 全部（不含小红书） |
| `--output` | `-o` | 输出目录 | `output/` |
| `--format` | — | 输出格式：`json` / `smcc` / `all` | `all` |

### 示例

```bash
# 全量抓取 → JSON + Markdown
python main.py

# 只看微博+知乎
python main.py --platform weibo,zhihu

# 只输出 SMCC 格式到桌面
python main.py --format smcc --output ~/Desktop/hotspots

# 输出到 SMCC 项目原料库
python main.py --format smcc --output /home/jiaod/smcc/00-原料/热点调研
```

### 输出产物

```
output/
├── 20260614.json              # JSON 原始数据
└── smcc/
    └── 2026-06-14.md          # SMCC 标准 Markdown
```

### 发送到飞书

```bash
lark-cli im +messages-send \
  --chat-id oc_d2e8df3c676afa2c352d8ece0a9b6141 \
  --markdown "$(cat output/smcc/2026-06-14.md)"
```

---

## Phase 2：选题正文内容抓取

当 Phase 1 的热点标题被选中后，写作 Agent 可以调用此功能抓取完整正文作为素材。

### 使用方式

```bash
# 给定标题 + URL 抓取正文
python main.py --content "选题标题" --content-url "https://..."

# 只给 URL（自动提取正文）
python main.py --content-url "https://news.sina.com.cn/xxx"

# 指定输出目录
python main.py --content "标题" --content-url "..." --output /素材目录
```

### 输出

素材文件保存在 `output/content/YYYYMMDD-标题.md`，格式：

```markdown
# 文章标题

**来源：** chinanews.com
**原文链接：** https://...
**抓取时间：** 2026-06-16 10:00

---

正文内容...

---

*🤖 HotRadar 内容抓取 · 2026-06-16 10:00*
```

### 技术实现

`platforms/content.py` 使用三层提取：
1. **requests + trafilatura** — 快速提取普通网页正文
2. **Playwright 渲染 + trafilatura** — 处理 JS 动态页面
3. 输出标准化 Markdown 素材格式

### 限制

- **知乎 / 微博 / 小红书**：反爬严格，URL 直提取消率低
- 写作 Agent 可通过 web_search 找到原文 URL 后传入

---

## 项目架构

```
hotradar/
├── main.py                 # 🚀 入口：CLI 解析 → 调度爬虫 → 输出
├── config.py               # ⚙️ 配置：日志设置、平台参数
├── README.md               # 📖 本文件
├── requirements.txt        # 📦 依赖清单
└── platforms/
    ├── __init__.py          # 导出爬虫类
    ├── base.py              # HotItem 数据模型 + BaseSpider 抽象基类
    ├── tophub.py            # 🧠 核心：tophub.today 聚合爬虫
    ├── xiaohongshu.py       # ⏳ 小红书爬虫（待攻关）
    ├── weibo.py             # 🗑️ 旧版微博爬虫（备用）
    ├── douyin.py            # 🗑️ 旧版抖音爬虫（备用）
    └── zhihu.py             # 🗑️ 旧版知乎爬虫（备用）
```

### 核心文件说明

| 文件 | 职责 | 维护要点 |
|------|------|----------|
| `main.py` | CLI 参数解析、调度爬虫、格式输出 | 如需增加输出目标（如数据库）在此修改 |
| `config.py` | 日志配置、User-Agent | 一般无需修改 |
| `platforms/base.py` | `HotItem` 数据类、`BaseSpider` 抽象类 | 如需扩展数据字段在此修改 |
| `platforms/tophub.py` | **核心爬虫**：Playwright 渲染 tophub.today 首页，解析文本 | 如果 tophub.today 改版，需要调整 `SECTIONS` 中的平台名/区段名，或 `_extract_section` 的解析逻辑 |
| `platforms/xiaohongshu.py` | 小红书爬虫（当前不可用） | 需浏览器登录态方案 |

---

## 爬虫工作原理

### tophub.today 爬虫（`tophub.py`）

```
Playwright 启动 Chromium
        ↓
打开 tophub.today 首页
        ↓
等待 5s 让 JS 懒加载完成
        ↓
获取 body.inner_text()
        ↓
按区段匹配（"微博"+"热搜榜" / "知乎"+"热榜" / "抖音"+"总榜"）
        ↓
解析编号列表：序号 / 标题 / 热度值
        ↓
返回 HotItem 列表
```

### 页面结构示意

tophub.today 首页的文本结构：

```
微博
热搜榜
1
小县城取消中考选拔全员直升高中
109万
2
39岁女子1天3杯奶茶喝出牛奶血
78万
...
7分钟前            ← 区段结束标记
知乎
热榜
1
网友揭秘「安徽无为板鸭其实是鹅」
885 万热度
...
```

**如果 tophub.today 改版导致抓不到数据：**
1. 手动打开 `https://tophub.today/`，检查页面文本是否变了
2. 修改 `tophub.py` 中 `SECTIONS` 列表里的平台名/区段名
3. 或修改 `_extract_section` 中的解析逻辑

---

## 当前限制

### 小红书 ❌

小红书有极严格的反爬机制：
- Cloudflare 防护
- IP 封锁（当前环境已被封）
- 需要登录态才能获取内容

**攻关方向：** 参考 `D:\jiaod\.easyclaw\workspace-xhs-operator-1\skills\xiaohongshu-search\SKILL.md`
该方案使用 Playwright 启动用户已登录小红书的 Chrome 浏览器来绕过反爬。

### tophub.today 依赖 ⚠️

项目强依赖 tophub.today 的页面结构。如果该站点改版或下线，爬虫会失效，届时需要：
1. 寻找替代聚合站
2. 或恢复各个平台的独立爬虫（旧版代码仍在 `platforms/` 中保留）

---

## 维护清单

### 日常维护

- [ ] **登录态检查**：Playwright 需要 Chromium 浏览器引擎，首次使用需运行 `python -m playwright install chromium`
- [ ] **数据验证**：定期 `python main.py` 检查各平台是否正常输出
- [ ] **tophub.today 可用性**：如果抓取为空，先手动打开 https://tophub.today/ 确认站点正常

### 故障排查

| 现象 | 可能原因 | 解决 |
|------|----------|------|
| Playwright 报错 | 浏览器引擎未安装 | `python -m playwright install chromium` |
| 微博/知乎/抖音数据为 0 | tophub.today 改版 | 检查页面文本结构，更新 `tophub.py` 中的解析逻辑 |
| 小红书报错 | IP 被封 / 反爬 | 暂时无法解决，跳过该平台 |
| lark-cli 发送失败 | token 过期 | 重新登录 `lark-cli auth` |
| `output/` 目录无文件 | 输出路径未创建 | 指定 `--output` 参数 |

---

## 版本历史

| 日期 | 版本 | 说明 |
|------|------|------|
| 2026-06-14 | v2.0 | 重写为 tophub.today 聚合方案，稳定抓取 3 平台 |
| 2026-06-xx | v1.0 | 初版：各平台独立爬虫（已废弃） |
