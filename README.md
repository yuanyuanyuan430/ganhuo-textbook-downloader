# ganhuo-textbook-downloader

![Skill](https://img.shields.io/badge/claude-skill-blue)
![Python](https://img.shields.io/badge/python-stdlib_only-3776AB)
![Language](https://img.shields.io/badge/language-中文-green)

一个给 Claude / Codex / Agent 用的中国教材下载技能：用户只说自然语言，它会识别省份/城市、年级、学科、册别、大学教材线索，也能从封面/内页截图 OCR 出来的文字辅助匹配，从 [TapXWorld/ChinaTextbook](https://github.com/TapXWorld/ChinaTextbook) 排序候选并下载公开教材文件。

## 能做什么

- 从自然语言解析：`安徽合肥三年级语文上册`、`广东深圳七年级数学`、`上海高一英语必修第一册`。
- 覆盖上游 `大学/` 目录里的大学教材：`大一高数同济第七版上册`、`本科线代同济第五版`、`概率论浙大四版`。
- 支持封面/内页图片 OCR 或手动 OCR 文本：`新版译林 九上教材`、`Know yourself`、`Welcome to the unit` 这类可读线索会参与排序。
- 按省份/城市给教材版本候选加权排序，但不假装这是官方定版；非统编科目需要保留候选确认。
- 用户明确指定版本时优先尊重用户版本。
- 自动处理上游拆分文件：`.pdf.1`、`.pdf.2` -> `.pdf`。
- 返回本地文件路径、上游路径、来源 URL、排序原因。

## 快速使用

```bash
python3 scripts/china_textbook_downloader.py search "安徽 合肥 小学 三年级 语文 上册" --explain
python3 scripts/china_textbook_downloader.py search "广东 深圳 七年级 数学 上册" --limit 5 --json
python3 scripts/china_textbook_downloader.py search "大学 高等数学 同济 第七版 上册" --limit 5 --explain
python3 scripts/china_textbook_downloader.py search "新版译林 九上 英语" --cover-image "/absolute/path/to/screenshot.png" --explain
python3 scripts/china_textbook_downloader.py download "安徽 合肥 小学 三年级 语文 上册" --auto
```

在 Claude / Codex 里可这样说：

- `用 $ganhuo-textbook-downloader 帮我下载安徽合肥三年级语文上册。`
- `用 $ganhuo-textbook-downloader 找广东深圳七年级数学教材，先列候选。`
- `用 $ganhuo-textbook-downloader 下载上海高一英语必修第一册。`
- `用 $ganhuo-textbook-downloader 找大学高数同济第七版上册，先列候选。`
- `用 $ganhuo-textbook-downloader 根据这张封面截图匹配教材。`

## Claude Skill 结构

```text
.
├── .claude-plugin/plugin.json
├── SKILL.md
├── scripts/china_textbook_downloader.py
├── references/province-preferences.md
├── llms.txt
└── llms-full.txt
```

`SKILL.md` 是 Claude 标准 skill 入口；`.claude-plugin/plugin.json` 是最小 Claude Code plugin 壳。

## 验证

```bash
python3 scripts/china_textbook_downloader.py self-test
python3 scripts/china_textbook_downloader.py search "安徽 合肥 小学 三年级 语文 上册" --limit 3 --explain
python3 scripts/china_textbook_downloader.py search "大学 线性代数 同济 第五版" --limit 3 --explain
claude plugin validate .
```

## 边界

本项目只提供下载公开可访问 GitHub 资源的 Agent 技能和脚本；教材资源来自上游项目。省份版本匹配是候选排序，不是官方教材征订结论。大学教材目前以 `大学/` 目录的数学类资源为主，不是全学科本科教材库。封面/OCR 匹配只是辅助排序；如果上游没有精确版本，会列近似候选而不是伪装成已找到。不要用它绕过登录、付费、版权或访问限制。
