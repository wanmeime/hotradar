---
name: content-fetcher
description: HotRadar 正文素材抓取 — 给写作 Agent（老史）使用
---

# HotRadar 正文素材抓取

## 这是什么？

HotRadar 是 SMCC 工作流的**热点素材采集工具**，分两个阶段：

| 阶段 | 做什么 | 谁触发 |
|------|--------|--------|
| **Phase 1** | 每天抓取微博/知乎/抖音热榜前10 → 发飞书卡片 + 存原料库 | 定时任务自动 |
| **Phase 2** | 给定 URL → 抓取正文 → 输出素材文件 | **你（老史）写稿时调用** |

## 什么时候用这个 Skill？

当你的写作工作流走到这一步时：

```
老沈审题 → 选定一个热点 → 创建任务文件
       ↓
你（老史）领取任务 → 需要查资料
       ↓
  🔵 调用本 Skill 抓取原文正文 ← 你在这里
       ↓
   获取素材 → 开始写稿
```

## 怎么用？

### 前提

你手上要有**文章的 URL**。来源可以是：

1. **飞书群里的热点卡片** — 点开卡片找到相关文章链接
2. **搜索引擎搜标题** — 用 `web_search` 搜热点标题找到原文
3. **直接给已知 URL**

### 调用方式

```bash
cd /home/jiaod/hotradar

# 完整用法：标题 + URL
python main.py --content "热点标题" --content-url "https://..."

# 简洁用法：只给 URL（标题自动提取）
python main.py --content-url "https://news.xxx.com/article"

# 指定素材输出目录
python main.py --content "标题" --content-url "..." --output /素材目录
```

### 实际例子

```bash
# 例1：抓取搜狐新闻
python main.py --content "市场监管总局约谈山姆总部" \
  --content-url "https://www.sohu.com/a/1036789852_237556"

# 例2：抓取知乎问答
python main.py --content-url "https://www.zhihu.com/question/2049810638076130456"
```

## 输出格式

运行成功后，素材文件保存在 `output/content/YYYYMMDD-标题.md`，内容格式：

```markdown
# 文章标题

**来源：** sohu.com
**原文链接：** https://...
**抓取时间：** 2026-06-16 10:00

---

文章正文内容...
正文中的图片会以 ![配图](链接) 形式保留

---

*🤖 HotRadar 内容抓取 · 2026-06-16 10:00*
```

## 注意事项

1. **知乎/微博** 反爬较严，可能抓不到正文。优先找**新闻网站**（搜狐、新浪、央广等）的链接
2. **抖音** 是视频平台，没有正文可抓，跳过
3. 如果 URL 抓取失败，换一个来源网站重试
4. 素材里的图片链接可能有防盗链，必要时单独下载
5. 正文提取后建议人工核对一下完整性

## 快速检查

想确认工具是否正常：

```bash
cd /home/jiaod/hotradar
python main.py  # 跑一次 Phase 1，看能否正常出数据
```

## 项目位置

```
项目根目录：/home/jiaod/hotradar/
素材输出：  output/content/
热点数据：  output/2026MMDD.json
GitHub：    https://github.com/wanmeime/hotradar
