# china-textbook-downloader-skill

![Skill](https://img.shields.io/badge/agent-skill-blue)
![Python](https://img.shields.io/badge/python-stdlib_only-3776AB)
![Language](https://img.shields.io/badge/language-中文-green)

一个给 Agent 用的中国教材下载技能：按年级、学科、版本、册别，从 [TapXWorld/ChinaTextbook](https://github.com/TapXWorld/ChinaTextbook) 查找并下载公开 PDF 教材。

## 适合谁

- 家长、学生、老师：快速定位指定教材。
- 教研/资料整理者：按关键词批量查找候选教材。
- Codex/Claude/Agent 工作流：把“找教材、下载、返回路径”变成可执行步骤。

## 能做什么

- 按自然语言搜索教材：`小学 三年级 语文 上册`、`初二 物理 下册 人教版`。
- 从 GitHub 原始文件链接下载 PDF。
- 自动合并上游拆分文件：`.pdf.1`、`.pdf.2` -> `.pdf`。
- 返回本地文件路径、上游路径、来源 URL。

## 快速使用

```bash
python3 scripts/china_textbook_downloader.py search "小学 语文 三年级 上册"
python3 scripts/china_textbook_downloader.py download "初中 物理 八年级 下册 人教版" --out "$HOME/Downloads/ChinaTextbook" --first
```

在 Codex 里可这样说：

- `用 $china-textbook-downloader 帮我下载人教版小学三年级语文教材。`
- `用 $china-textbook-downloader 找七年级上册数学电子教材，能下载就保存到本地。`
- `用 $china-textbook-downloader 下载中国教材项目里的初中物理 PDF。`

## 文件结构

```text
.
├── SKILL.md
├── agents/openai.yaml
├── scripts/china_textbook_downloader.py
├── llms.txt
└── llms-full.txt
```

## 验证

```bash
python3 scripts/china_textbook_downloader.py self-test
python3 scripts/china_textbook_downloader.py search "小学 语文 三年级 上册" --limit 3
```

## 边界

本项目只提供下载公开可访问 GitHub 资源的 Agent 技能和脚本；教材资源来自上游项目。不要用它绕过登录、付费、版权或访问限制。
