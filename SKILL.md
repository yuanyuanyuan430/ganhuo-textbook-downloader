---
name: china-textbook-downloader
description: Find, list, and download public PDF textbooks from TapXWorld/ChinaTextbook on GitHub. Use when the user asks to download Chinese textbooks, find a textbook by grade/subject/version/semester, or says phrases like "技能帮我从这个项目下载对应的教科书", "下载人教版小学三年级语文", "找七年级上册数学教材", or "从 ChinaTextbook 下载教材".
---

# China Textbook Downloader

Use this skill to turn a natural-language textbook request into a searched and downloaded PDF from `TapXWorld/ChinaTextbook`.

## Workflow

1. Extract the textbook clues: stage, grade, subject, version, semester/book volume, and any exact title text.
2. Search before downloading:

```bash
python3 .agents/skills/china-textbook-downloader/scripts/china_textbook_downloader.py \
  search "小学 语文 三年级 上册"
```

3. If the top result is clearly the requested book, download it:

```bash
python3 .agents/skills/china-textbook-downloader/scripts/china_textbook_downloader.py \
  download "小学 语文 三年级 上册" \
  --out "$HOME/Downloads/ChinaTextbook" \
  --first
```

4. If multiple candidates are plausible, show the numbered list and ask the user which one to download.
5. Return the local file path, upstream GitHub path, and source URL.

## Commands

Search:

```bash
python3 .agents/skills/china-textbook-downloader/scripts/china_textbook_downloader.py \
  search "初中 物理 八年级 下册"
```

Download by result number:

```bash
python3 .agents/skills/china-textbook-downloader/scripts/china_textbook_downloader.py \
  download "初中 物理 八年级 下册" --pick 1
```

Refresh the GitHub tree cache:

```bash
python3 .agents/skills/china-textbook-downloader/scripts/china_textbook_downloader.py \
  search "高等数学" --refresh
```

Run the built-in check after editing the script:

```bash
python3 .agents/skills/china-textbook-downloader/scripts/china_textbook_downloader.py self-test
```

## Notes

- The script uses the GitHub tree API and `raw.githubusercontent.com`; no extra Python packages are required.
- Split files such as `.pdf.1` and `.pdf.2` are downloaded in numeric order and merged into one `.pdf`.
- Only download publicly accessible upstream files. Do not bypass login, payment, copyright, or access restrictions.
- If the user gives a vague request like "下载语文教材", ask for at least grade or stage before downloading.
