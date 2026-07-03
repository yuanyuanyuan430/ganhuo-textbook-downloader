---
name: ganhuo-textbook-downloader
description: Find, rank, and download public textbook files from TapXWorld/ChinaTextbook, including K-12 and the repository's university textbooks. Use this skill whenever the user asks in natural language to download Chinese textbooks, match a province/city/grade/subject/semester, identify a textbook from readable cover/page text or an image screenshot, infer likely textbook versions, or says phrases like "技能帮我从这个项目下载对应的教科书", "江苏九上译林英语", "大学高数同济第七版上册", or "根据这个封面找教材".
---

# Ganhuo Textbook Downloader

Use this skill to turn a natural-language textbook request into ranked candidates and, when safe, a downloaded textbook file from `TapXWorld/ChinaTextbook`.

## Workflow

1. Extract province/city, stage, grade, subject, version, semester/book volume, edition, publisher/school clues, and any exact title clues.
   - K-12 examples: `江苏九上译林英语`, `安徽合肥三年级语文上册`.
   - University examples: `大一高数同济第七版上册`, `本科线代同济第五版`, `概率论浙大四版`.
   - Cover/page image examples: OCR readable text such as `新版译林 九上教材`, `Know yourself`, `Welcome to the unit`.
2. Search first. Province and city words are used for ranking, not as required path tokens:

```bash
python3 "${CLAUDE_SKILL_DIR:-.}/scripts/china_textbook_downloader.py" \
  search "安徽 合肥 小学 三年级 语文 上册" --explain
```

3. If the user provides a cover/page screenshot, pass it as an OCR clue:

```bash
python3 "${CLAUDE_SKILL_DIR:-.}/scripts/china_textbook_downloader.py" \
  search "新版译林 九上 英语" \
  --cover-image "/absolute/path/to/screenshot.png" \
  --explain
```

4. If the user already supplied extracted cover text, pass it directly:

```bash
python3 "${CLAUDE_SKILL_DIR:-.}/scripts/china_textbook_downloader.py" \
  search "九上英语" \
  --ocr-text "新版译林 九上教材 Know yourself Welcome to the unit" \
  --explain
```

5. If one candidate clearly matches the user's request, download it:

```bash
python3 "${CLAUDE_SKILL_DIR:-.}/scripts/china_textbook_downloader.py" \
  download "安徽 合肥 小学 三年级 语文 上册" \
  --out "$HOME/Downloads/ChinaTextbook" \
  --auto
```

6. If multiple candidates are plausible, show the numbered list and ask the user which one to download. Province preferences and cover/OCR clues are ranking hints.
7. Return the local file path, upstream GitHub path, source URL, split-file status, and ranking reasons.

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

Search university textbooks:

```bash
python3 "${CLAUDE_SKILL_DIR:-.}/scripts/china_textbook_downloader.py" \
  search "大学 高等数学 同济 第七版 上册" --limit 5 --explain
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

## University Matching

The upstream repository currently stores university resources under `大学/`, mainly math-related subjects such as `高等数学`, `线性代数`, `离散数学`, and `概率论`.

- Map natural language such as `本科`, `高校`, `大一`, `高数`, `线代`, `离散`, `数统`, and `概率统计` into repository terms.
- Use edition and source clues such as `同济`, `浙大`, `第五版`, `第六版`, `第七版`, `四版`, and `原书` as strong matching terms.
- Demote non-main materials such as `答案`, `习题`, `全解`, `解析`, `学习辅导`, `附册`, and `指南` unless the user explicitly asks for them.
- If the requested university edition is absent, report the closest candidates instead of pretending a near miss is correct.

## Cover And OCR Matching

The script can use readable text from a cover or page screenshot. It runs local `tesseract` OCR when available and accepts `--ocr-text` when text has already been extracted.

- Useful clues: title, version/publisher, grade/volume, unit title, edition, author/editor, school/publisher names.
- Noisy clues from phone/PDF viewer UI are filtered where possible.
- OCR clues help ranking; they are not proof that the exact edition exists in the upstream repository.

## Boundaries

- Only download publicly accessible upstream GitHub files. Do not bypass login, payment, copyright, or access restrictions.
- Do not promise that the province ranking is authoritative or current for every school.
- Do not auto-download when grade, subject, or book volume is unclear and multiple candidates exist.
- Do not auto-download a near-miss university edition, such as a fifth edition when the user asked for the sixth edition.
- Split files such as `.pdf.1` and `.pdf.2` are byte chunks; the script downloads them in numeric order and concatenates them into one `.pdf`.
