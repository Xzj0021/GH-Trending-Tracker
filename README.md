# GH-Trending-Tracker — GitHub 热点追踪器

自动抓取 GitHub Trending 页面，用 AI 对热门仓库进行分类和趋势分析，每日生成 Markdown 报告。支持 GitHub Actions 全自动运行。

## 工作原理

```
GitHub Trending 页面 → BeautifulSoup 解析 → RepoInfo 结构化数据
  → Analyzer 分析引擎
    ├── 13 类 AI 关键词分类（大模型/Web/DevOps/安全...）
    ├── 新上榜检测（历史对比）
    ├── 星标增长速度排名
    └── 语言分布统计
  → Reporter → Markdown 日报
```

## 功能特性

- **Trending 爬虫**：支持 daily/weekly/monthly 三个时间维度，可按语言过滤
- **智能分类**：基于关键词 NLP 的 13 大类别自动标注
- **趋势检测**：新上榜项目 + 快速增长项目识别
- **历史对比**：本地 JSON 快照，对比星标增长
- **AI 摘要**：可选 OpenAI API 集成，生成中文趋势分析
- **全自动**：GitHub Actions 每日 08:27 UTC 运行，自动提交报告

## 安装

```bash
pip install -r requirements.txt
```

## 使用

```bash
# 默认：每日总榜
python -m src.main

# 所有主流语言 Top 10
python -m src.main --all-languages

# 只看 Python
python -m src.main --language python --since weekly

# AI 中文摘要（需设置 OPENAI_API_KEY）
python -m src.main --all-languages --ai

# 指定输出路径
python -m src.main --all-languages --output report.md
```

## 报告示例

```markdown
# GitHub 热点追踪日报
日期: 2026-06-12 | 更新时间: 08:27 UTC
收录仓库: 85 个

## 今日最热 (Star 增长最快)
| 仓库 | 描述 | 语言 | 总 Stars | 今日新增 |
|------|------|------|----------|----------|
...

## 分类浏览
### AI / 大模型 (12 个)
- [owner/repo] — 描述
...
```

## 分类体系

`AI/大模型` · `机器学习/数据科学` · `Web/前端` · `后端/API` · `DevOps/基础设施` · `数据库/存储` · `CLI/工具` · `安全/隐私` · `区块链/加密货币` · `移动端` · `游戏开发` · `文档/知识管理`

## 许可

MIT License
