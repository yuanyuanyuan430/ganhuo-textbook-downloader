---
name: ganhuo-textbook-downloader
description: Find, rank, and download public PDF textbooks from TapXWorld/ChinaTextbook. Use this skill whenever the user asks in natural language to download Chinese textbooks, find matching textbooks for a province/city/grade/subject/semester, infer the likely textbook version for a province, or says phrases like "技能帮我从这个项目下载对应的教科书", "安徽合肥三年级语文上册", "广东七年级数学教材", "上海高一英语必修第一册", or "从 ChinaTextbook 下载教材".
---

# Ganhuo Textbook Downloader

Use this skill to turn a natural-language textbook request into ranked candidates and, when safe, a downloaded PDF from `TapXWorld/ChinaTextbook`.

## Workflow

1. Extract province/city, stage, grade, subject, version, semester/book volume, and any exact title clues.
2. Search first. Province and city words are used for ranking, not as required path tokens:

```bash
python3 "${CLAUDE_SKILL_DIR:-.}/scripts/china_textbook_downloader.py" \
  search "安徽 合肥 小学 三年级 语文 上册" --explain
```

3. If one candidate clearly matches the user's request, download it:

```bash
python3 "${CLAUDE_SKILL_DIR:-.}/scripts/china_textbook_downloader.py" \
  download "安徽 合肥 小学 三年级 语文 上册" \
  --out "$HOME/Downloads/ChinaTextbook" \
  --auto
```

4. If multiple candidates are plausible, show the numbered list and ask the user which one to download. Province preferences are only ranking hints.
5. Return the local file path, upstream GitHub path, source URL, and ranking reasons.

## Commands

Search with province inference:

```bash
python3 "${CLAUDE_SKILL_DIR:-.}/scripts/china_textbook_downloader.py" \
  search "广东 深圳 七年级 数学 上册" --limit 5 --explain
```

Override province when the user implies location outside the text:

```bash
python3 "${CLAUDE_SKILL_DIR:-.}/scripts/china_textbook_downloader.py" \
  search "七年级 数学 上册" --province 江苏 --explain
```

Download by result number:

```bash
python3 "${CLAUDE_SKILL_DIR:-.}/scripts/china_textbook_downloader.py" \
  download "上海 高一 英语 必修 第一册" --pick 1
```

Run the built-in check after editing the script:

```bash
python3 "${CLAUDE_SKILL_DIR:-.}/scripts/china_textbook_downloader.py" self-test
```

## Province Matching

The script uses province/city clues to boost likely textbook versions. It does not claim an official province-to-textbook assignment.

- For `语文`, `道德与法治`, and `历史`, prefer `统编版` because these are commonly unified subjects.
- For other subjects, use province/city preference hints such as `江苏 -> 苏教版/译林版`, `北京 -> 北京版/外研版/北师大版`, `上海 -> 沪教版`, `深圳/广东 -> 北师大版/沪教版/人教版`, and broader `人教版` fallbacks.
- If the user explicitly names a version, the explicit version wins over province preferences.
- If the request is vague or candidate rankings are close, ask the user to choose.

Read `references/province-preferences.md` only when you need to explain the limitation to the user or update the province preference table.

## Boundaries

- Only download publicly accessible upstream GitHub files. Do not bypass login, payment, copyright, or access restrictions.
- Do not promise that the province ranking is authoritative or current for every school.
- Do not auto-download when grade, subject, or book volume is unclear and multiple candidates exist.
- Split files such as `.pdf.1` and `.pdf.2` are byte chunks; the script downloads them in numeric order and concatenates them into one `.pdf`.
