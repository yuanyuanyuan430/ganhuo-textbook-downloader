#!/usr/bin/env python3
"""Search and download PDFs from TapXWorld/ChinaTextbook."""

from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
import time
import unicodedata
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass
from dataclasses import field
from pathlib import Path

REPO = "TapXWorld/ChinaTextbook"
BRANCH = "master"
TREE_API = f"https://api.github.com/repos/{REPO}/git/trees/{BRANCH}?recursive=1"
RAW_BASE = f"https://raw.githubusercontent.com/{REPO}/{BRANCH}/"
CACHE_PATH = Path(os.environ.get("XDG_CACHE_HOME", Path.home() / ".cache")) / "ganhuo-textbook-downloader" / "tree-v2.json"
CACHE_TTL_SECONDS = 24 * 60 * 60
DEFAULT_OUT = Path.home() / "Downloads" / "ChinaTextbook"
SUPPORTED_FILE_RE = re.compile(r"\.(?:pdf(?:\.\d+)?|djvu)$", re.IGNORECASE)

ALIASES = {
    "新版译林": "译林版 新版",
    "新译林": "译林版 新版",
    "牛津译林": "译林版",
    "译林英语": "译林版 英语",
    "初一": "七年级",
    "初二": "八年级",
    "初三": "九年级",
    "高一": "高中",
    "高二": "高中",
    "高三": "高中",
    "小一": "一年级",
    "小二": "二年级",
    "小三": "三年级",
    "小四": "四年级",
    "小五": "五年级",
    "小六": "六年级",
    "政治": "思想政治",
    "生物": "生物学",
    "高数": "高等数学",
    "线代": "线性代数",
    "概率统计": "概率论与数理统计",
    "概统": "概率论与数理统计",
    "第四版": "四版",
    "第4版": "四版",
    "第5版": "第五版",
    "第6版": "第六版",
    "第7版": "第七版",
    "第8版": "第八版",
    "本科": "大学",
    "高校": "大学",
    "高等教育": "大学",
}

KEYWORDS = [
    "选择性必修",
    "体育与健康",
    "道德与法治",
    "思想政治",
    "人民教育出版社",
    "概率论与数理统计",
    "高等数学",
    "线性代数",
    "离散数学",
    "大学物理",
    "大学英语",
    "数理统计",
    "概率论",
    "程序设计",
    "数据结构",
    "操作系统",
    "计算机网络",
    "C语言程序设计",
    "原书",
    "信息技术",
    "通用技术",
    "计算机",
    "同济大学",
    "浙江大学",
    "同济",
    "浙大",
    "第八版",
    "第8版",
    "第七版",
    "第7版",
    "第六版",
    "第6版",
    "第五版",
    "第5版",
    "四版",
    "一年级",
    "二年级",
    "三年级",
    "四年级",
    "五年级",
    "六年级",
    "七年级",
    "八年级",
    "九年级",
    "上册",
    "下册",
    "全一册",
    "第一册",
    "第二册",
    "第三册",
    "第四册",
    "必修第一册",
    "必修第二册",
    "必修第三册",
    "必修",
    "小学",
    "初中",
    "高中",
    "大学",
    "新版",
    "语文",
    "数学",
    "英语",
    "物理",
    "化学",
    "历史",
    "地理",
    "科学",
    "美术",
    "艺术",
    "音乐",
    "俄语",
    "日语",
    "书法",
    "人教版",
    "人教A版",
    "统编版",
    "北师大",
    "北师大版",
    "苏教版",
    "沪教版",
    "北京版",
    "浙教版",
    "粤教版",
    "译林版",
    "鲁教版",
    "鲁科版",
    "青岛版",
    "华东师大版",
    "外研版",
]

DROP_WORDS = {
    "帮我",
    "下载",
    "查找",
    "寻找",
    "找到",
    "根据",
    "封面",
    "图片",
    "截图",
    "扫描",
    "识别",
    "ocr",
    "OCR",
    "里的",
    "教材",
    "教科书",
    "电子版",
    "pdf",
    "PDF",
    "公开",
    "对应",
    "这个",
    "项目",
    "里面",
}

PROVINCE_ALIASES = {
    "北京": "北京",
    "北京市": "北京",
    "上海": "上海",
    "上海市": "上海",
    "天津": "天津",
    "天津市": "天津",
    "重庆": "重庆",
    "重庆市": "重庆",
    "安徽": "安徽",
    "安徽省": "安徽",
    "江苏": "江苏",
    "江苏省": "江苏",
    "广东": "广东",
    "广东省": "广东",
    "浙江": "浙江",
    "浙江省": "浙江",
    "河南": "河南",
    "河南省": "河南",
    "山东": "山东",
    "山东省": "山东",
    "四川": "四川",
    "四川省": "四川",
    "湖北": "湖北",
    "湖北省": "湖北",
    "湖南": "湖南",
    "湖南省": "湖南",
    "福建": "福建",
    "福建省": "福建",
    "江西": "江西",
    "江西省": "江西",
    "河北": "河北",
    "河北省": "河北",
    "山西": "山西",
    "山西省": "山西",
    "陕西": "陕西",
    "陕西省": "陕西",
    "辽宁": "辽宁",
    "辽宁省": "辽宁",
    "吉林": "吉林",
    "吉林省": "吉林",
    "黑龙江": "黑龙江",
    "黑龙江省": "黑龙江",
    "云南": "云南",
    "云南省": "云南",
    "贵州": "贵州",
    "贵州省": "贵州",
    "广西": "广西",
    "广西壮族自治区": "广西",
    "海南": "海南",
    "海南省": "海南",
    "甘肃": "甘肃",
    "甘肃省": "甘肃",
    "青海": "青海",
    "青海省": "青海",
    "宁夏": "宁夏",
    "宁夏回族自治区": "宁夏",
    "新疆": "新疆",
    "新疆维吾尔自治区": "新疆",
    "内蒙古": "内蒙古",
    "内蒙古自治区": "内蒙古",
    "西藏": "西藏",
    "西藏自治区": "西藏",
    "全国": "全国",
}

CITY_TO_PROVINCE = {
    "合肥": "安徽",
    "芜湖": "安徽",
    "南京": "江苏",
    "苏州": "江苏",
    "无锡": "江苏",
    "常州": "江苏",
    "南通": "江苏",
    "杭州": "浙江",
    "宁波": "浙江",
    "温州": "浙江",
    "广州": "广东",
    "深圳": "广东",
    "佛山": "广东",
    "东莞": "广东",
    "郑州": "河南",
    "洛阳": "河南",
    "济南": "山东",
    "青岛": "山东",
    "成都": "四川",
    "绵阳": "四川",
}

SUBJECTS = [
    "道德与法治",
    "思想政治",
    "体育与健康",
    "信息技术",
    "通用技术",
    "概率论与数理统计",
    "生物学",
    "高等数学",
    "线性代数",
    "离散数学",
    "大学物理",
    "大学英语",
    "数理统计",
    "概率论",
    "程序设计",
    "数据结构",
    "操作系统",
    "计算机网络",
    "C语言程序设计",
    "计算机",
    "语文",
    "数学",
    "英语",
    "物理",
    "化学",
    "历史",
    "地理",
    "科学",
    "美术",
    "音乐",
    "艺术",
    "日语",
    "俄语",
    "书法",
]

CORE_UNIFIED_SUBJECTS = {"语文", "道德与法治", "历史"}
UNIVERSITY_SUBJECTS = {"高等数学", "线性代数", "离散数学", "概率论", "概率论与数理统计", "数理统计", "大学物理", "大学英语", "程序设计", "数据结构", "操作系统", "计算机网络", "C语言程序设计", "计算机"}
NON_TEXTBOOK_WORDS = ("练习", "习题", "答案", "全解", "解析", "辅导", "学习辅导", "指南", "附册", "教师", "教师用书", "活动手册", "书法练习")
VERSION_WORDS = ("统编版", "人教版", "人教A版", "北师大", "北师大版", "苏教版", "沪教版", "北京版", "浙教版", "粤教版", "译林版", "鲁教版", "鲁科版", "青岛版", "华东师大版", "外研版")
GRADE_STAGE = {
    "一年级": "小学",
    "二年级": "小学",
    "三年级": "小学",
    "四年级": "小学",
    "五年级": "小学",
    "六年级": "小学",
    "七年级": "初中",
    "八年级": "初中",
    "九年级": "初中",
}
COVER_NOISE_WORDS = {
    "目录",
    "预览模式",
    "播放演示",
    "云打印",
    "手机",
    "电量",
    "wifi",
    "返回",
}

# ponytail: province hints are ranking nudges, not official textbook assignments.
PROVINCE_PREFERENCES = {
    "全国": {"default": ["统编版", "人教版", "人民教育出版社"]},
    "安徽": {"default": ["统编版", "人教版", "人民教育出版社"], "英语": ["人教版"], "数学": ["人教版"]},
    "江苏": {"default": ["统编版", "苏教版", "译林版", "人民教育出版社"], "数学": ["苏教版", "人教版"], "英语": ["译林版", "人教版"], "物理": ["苏教版", "人教版"]},
    "北京": {"default": ["统编版", "北京版", "北师大版", "人教版", "人民教育出版社"], "数学": ["北京版", "人教版", "北师大版"], "英语": ["外研版", "北京版", "人教版"], "物理": ["北师大版", "人教版"]},
    "上海": {"default": ["统编版", "沪教版", "上海教育出版社", "人教版"], "英语": ["沪教版", "人教版"], "数学": ["沪教版", "人教版"]},
    "广东": {"default": ["统编版", "人教版", "粤教版", "外研版"], "英语": ["沪教版", "外研版", "人教版"], "数学": ["北师大版", "人教版"]},
    "浙江": {"default": ["统编版", "浙教版", "人教版"], "数学": ["浙教版", "人教版"], "科学": ["浙教版", "华东师大版"]},
    "河南": {"default": ["统编版", "人教版", "人民教育出版社"], "英语": ["人教版"], "数学": ["人教版"]},
    "山东": {"default": ["统编版", "鲁教版", "鲁科版", "人教版", "人民教育出版社"], "英语": ["鲁教版", "人教版"], "数学": ["鲁教版", "人教版", "青岛版"], "物理": ["鲁科版", "人教版"], "生物学": ["鲁科版", "人教版"]},
    "四川": {"default": ["统编版", "人教版", "人民教育出版社"], "英语": ["人教版"], "数学": ["人教版"]},
}


@dataclass
class Result:
    path: str
    parts: list[str]
    score: int
    matched: int
    reasons: list[str] = field(default_factory=list)

    @property
    def split(self) -> bool:
        return len(self.parts) > 1 or self.parts[0] != self.path

    @property
    def url(self) -> str:
        return raw_url(self.path if not self.split else self.parts[0])


@dataclass
class RequestProfile:
    province: str | None = None
    location: str | None = None
    stage: str | None = None
    subject: str | None = None
    explicit_versions: list[str] = field(default_factory=list)


def raw_url(path: str) -> str:
    return RAW_BASE + urllib.parse.quote(path, safe="/")


def expand_compact_terms(text: str) -> str:
    text = unicodedata.normalize("NFKC", text)
    grade_map = {
        "一": "一年级",
        "二": "二年级",
        "三": "三年级",
        "四": "四年级",
        "五": "五年级",
        "六": "六年级",
        "七": "七年级",
        "八": "八年级",
        "九": "九年级",
        "1": "一年级",
        "2": "二年级",
        "3": "三年级",
        "4": "四年级",
        "5": "五年级",
        "6": "六年级",
        "7": "七年级",
        "8": "八年级",
        "9": "九年级",
    }
    semester_map = {"上": "上册", "下": "下册", "a": "上册", "A": "上册", "b": "下册", "B": "下册"}

    def replace_grade_semester(match: re.Match[str]) -> str:
        return f" {grade_map[match.group(1)]} {semester_map[match.group(2)]} "

    text = re.sub(r"(?<!浙)大\s*[一二三四1-4]", "大学", text)
    text = re.sub(r"离散(?!数学)", "离散数学", text)
    text = re.sub(r"数统", "概率论与数理统计", text)
    text = text.replace("微积分", "高等数学")
    text = re.sub(r"高数\s*上册?", "高等数学 上册", text)
    text = re.sub(r"高数\s*下册?", "高等数学 下册", text)
    text = re.sub(r"初\s*([一二三])\s*([上下])", lambda match: f" {ALIASES['初' + match.group(1)]} {semester_map[match.group(2)]} ", text)
    text = re.sub(r"小\s*([一二三四五六])\s*([上下])", lambda match: f" {ALIASES['小' + match.group(1)]} {semester_map[match.group(2)]} ", text)
    text = re.sub(r"([一二三四五六七八九1-9])\s*年级\s*([上下])", replace_grade_semester, text)
    text = re.sub(r"(?<!第)([一二三四五六七八九1-9])\s*([上下])", replace_grade_semester, text)
    text = re.sub(r"\b([7-9])\s*([AaBb])\b", replace_grade_semester, text)
    text = re.sub(r"高[一二三1-3]\s*([上下])", lambda match: f" 高中 {semester_map[match.group(1)]} ", text)
    return text


def normalize(text: str) -> str:
    text = unicodedata.normalize("NFKC", text).lower()
    for old, new in ALIASES.items():
        text = text.replace(old.lower(), new.lower())
    return re.sub(r"[\s/_·・（）()【】\[\]《》<>:：,，.。、\-]+", "", text)


def extract_profile(query: str, province_override: str | None = None) -> RequestProfile:
    profile = RequestProfile()
    normalized = expand_compact_terms(query)
    for old, new in ALIASES.items():
        normalized = normalized.replace(old, new)

    if province_override:
        province = PROVINCE_ALIASES.get(province_override, PROVINCE_ALIASES.get(province_override.rstrip("省市"), province_override))
        profile.province = province
        profile.location = province_override

    for city, province in CITY_TO_PROVINCE.items():
        if city in normalized and not profile.province:
            profile.province = province
            profile.location = city
            break

    for alias, province in PROVINCE_ALIASES.items():
        if alias in normalized:
            profile.province = profile.province or province
            profile.location = profile.location or alias
            break

    for subject in sorted(SUBJECTS, key=len, reverse=True):
        if subject in normalized:
            profile.subject = subject
            break

    for stage in ("小学", "初中", "高中", "大学"):
        if stage in normalized:
            profile.stage = stage
            break
    if not profile.stage and profile.subject in UNIVERSITY_SUBJECTS:
        profile.stage = "大学"
    if not profile.stage:
        for grade, stage in GRADE_STAGE.items():
            if grade in normalized:
                profile.stage = stage
                break

    for version in VERSION_WORDS:
        if version in normalized:
            profile.explicit_versions.append(version)

    return profile


def strip_location_words(query: str) -> str:
    stripped = query
    for word in sorted([*PROVINCE_ALIASES.keys(), *CITY_TO_PROVINCE.keys()], key=len, reverse=True):
        stripped = stripped.replace(word, " ")
    return stripped


def query_tokens(query: str, profile: RequestProfile | None = None) -> list[str]:
    query = strip_location_words(query)
    normalized_query = expand_compact_terms(query)
    for old, new in ALIASES.items():
        normalized_query = normalized_query.replace(old, new)
    for word in DROP_WORDS:
        normalized_query = normalized_query.replace(word, " ")

    tokens: list[str] = []
    leftovers = normalized_query
    for word in sorted(KEYWORDS, key=len, reverse=True):
        if word in leftovers:
            tokens.append(normalize(word))
            leftovers = leftovers.replace(word, " ")

    for piece in re.split(r"\s+", leftovers):
        piece = piece.strip()
        if not piece or piece in DROP_WORDS:
            continue
        token = normalize(piece)
        if token and token not in {normalize(w) for w in DROP_WORDS}:
            tokens.append(token)

    seen: set[str] = set()
    return [token for token in tokens if not (token in seen or seen.add(token))]


def clean_cover_text(text: str) -> str:
    lines: list[str] = []
    for line in text.splitlines():
        stripped = line.strip()
        if not stripped:
            continue
        normalized = normalize(stripped)
        if any(normalize(word) in normalized for word in COVER_NOISE_WORDS):
            continue
        if re.fullmatch(r"[\d:：<>\s|=_\-@©]+", stripped):
            continue
        lines.append(stripped)
    return "\n".join(lines)


def cover_text_from_image(path: str) -> tuple[str, list[str]]:
    image_path = Path(path).expanduser()
    if not image_path.exists():
        raise SystemExit(f"Cover image not found: {image_path}")

    texts: list[str] = []
    notes: list[str] = []
    stem = image_path.stem
    if stem and not stem.startswith("codex-clipboard"):
        texts.append(stem)
        notes.append("cover filename clues")

    tesseract = shutil.which("tesseract")
    if not tesseract:
        notes.append("cover OCR skipped: tesseract not found")
        return "\n".join(texts), notes

    for lang in ("chi_sim+eng", "eng"):
        try:
            completed = subprocess.run(
                [tesseract, str(image_path), "stdout", "-l", lang],
                check=False,
                capture_output=True,
                text=True,
                timeout=25,
            )
        except (OSError, subprocess.TimeoutExpired):
            continue
        cleaned = clean_cover_text(completed.stdout)
        if completed.returncode == 0 and cleaned:
            texts.append(cleaned)
            notes.append(f"cover OCR clues ({lang})")
            break
    else:
        notes.append("cover OCR produced no usable text")

    return "\n".join(texts), notes


def build_effective_query(query: str, cover_image: str | None = None, ocr_text: str | None = None) -> tuple[str, list[str]]:
    parts = [query]
    notes: list[str] = []
    if ocr_text:
        cleaned = clean_cover_text(ocr_text)
        if cleaned:
            parts.append(cleaned)
            notes.append("supplied cover text clues")
    if cover_image:
        cover_text, cover_notes = cover_text_from_image(cover_image)
        if cover_text:
            parts.append(cover_text)
        notes.extend(cover_notes)
    return "\n".join(parts), notes


def add_context_reasons(results: list[Result], notes: list[str]) -> None:
    if not notes:
        return
    for result in results:
        result.reasons = [*notes, *result.reasons]


def preference_terms(profile: RequestProfile) -> list[str]:
    terms: list[str] = []
    if profile.subject in CORE_UNIFIED_SUBJECTS:
        terms.extend(["统编版", "人民教育出版社", "人教版"])
    province = profile.province or "全国"
    prefs = PROVINCE_PREFERENCES.get(province, PROVINCE_PREFERENCES["全国"])
    terms.extend(prefs.get(profile.subject or "", []))
    terms.extend(prefs.get("default", []))

    seen: set[str] = set()
    return [term for term in terms if not (term in seen or seen.add(term))]


def fetch_json(url: str) -> dict:
    request = urllib.request.Request(url, headers={"User-Agent": "ganhuo-textbook-downloader"})
    with urllib.request.urlopen(request, timeout=30) as response:
        return json.loads(response.read().decode("utf-8"))


def load_tree(refresh: bool = False) -> list[str]:
    if not refresh and CACHE_PATH.exists() and time.time() - CACHE_PATH.stat().st_mtime < CACHE_TTL_SECONDS:
        return json.loads(CACHE_PATH.read_text(encoding="utf-8"))

    data = fetch_json(TREE_API)
    paths = [
        item["path"]
        for item in data.get("tree", [])
        if item.get("type") == "blob"
        and not item.get("path", "").startswith(".cache/")
        and SUPPORTED_FILE_RE.search(item.get("path", ""))
    ]
    CACHE_PATH.parent.mkdir(parents=True, exist_ok=True)
    CACHE_PATH.write_text(json.dumps(paths, ensure_ascii=False, indent=2), encoding="utf-8")
    return paths


def group_pdf_parts(paths: list[str]) -> dict[str, list[str]]:
    groups: dict[str, list[str]] = {}
    for path in paths:
        merge_folder = re.search(r"(.+\.pdf)_merge_folder/.+\.pdf\.\d+$", path, re.IGNORECASE)
        base = merge_folder.group(1) if merge_folder else re.sub(r"\.pdf\.\d+$", ".pdf", path, flags=re.IGNORECASE)
        groups.setdefault(base, []).append(path)

    return {
        base: [base] if base in parts else sorted(parts, key=part_number)
        for base, parts in groups.items()
    }


def part_number(path: str) -> int:
    match = re.search(r"\.pdf\.(\d+)$", path, re.IGNORECASE)
    return int(match.group(1)) if match else 0


def search(paths: list[str], query: str, limit: int, province: str | None = None) -> list[Result]:
    profile = extract_profile(query, province_override=province)
    tokens = query_tokens(query, profile)
    if not tokens:
        raise SystemExit("Please include grade, subject, version, or title keywords.")

    results: list[Result] = []
    for base, parts in group_pdf_parts(paths).items():
        haystack = normalize(base)
        matched = sum(1 for token in tokens if token in haystack)
        if matched == 0:
            continue
        score = matched * 100 - len(base)
        reasons: list[str] = []
        if matched == len(tokens):
            score += 1000
            reasons.append("all query terms matched")

        if profile.stage:
            if base.startswith(profile.stage + "/"):
                score += 160
                reasons.append(f"stage match: {profile.stage}")
        elif profile.subject in UNIVERSITY_SUBJECTS and base.startswith("大学/"):
            score += 120
            reasons.append("university subject match")

        for version in profile.explicit_versions:
            if normalize(version) in haystack:
                score += 500
                reasons.append(f"explicit version: {version}")

        if not profile.explicit_versions:
            for rank, term in enumerate(preference_terms(profile), 1):
                if normalize(term) in haystack:
                    bump = max(20, 140 - rank * 20)
                    score += bump
                    source = f"{profile.province} preference" if profile.province else "default preference"
                    reasons.append(f"{source}: {term}")
                    break

        if any(normalize(word) in haystack for word in NON_TEXTBOOK_WORDS) and not any(word in query for word in NON_TEXTBOOK_WORDS):
            score -= 220
            reasons.append("demoted non-main textbook material")

        results.append(Result(base, parts, score, matched, reasons))

    full_matches = [result for result in results if result.matched == len(tokens)]
    chosen = full_matches or results
    chosen.sort(key=lambda result: (-result.score, result.path))
    return chosen[:limit]


def confidence_ok(results: list[Result], tokens: list[str]) -> bool:
    if not results or len(tokens) < 3:
        return False
    if results[0].matched < min(3, len(tokens)):
        return False
    if len(results) == 1:
        return True
    return results[0].score - results[1].score >= 120


def download_file(url: str, destination: Path, overwrite: bool = False) -> None:
    if destination.exists() and not overwrite:
        return
    partial = destination.with_name(destination.name + ".part")
    request = urllib.request.Request(url, headers={"User-Agent": "ganhuo-textbook-downloader"})
    with urllib.request.urlopen(request, timeout=60) as response, partial.open("wb") as output:
        while True:
            chunk = response.read(1024 * 1024)
            if not chunk:
                break
            output.write(chunk)
    partial.replace(destination)


def download_result(result: Result, out_dir: Path, overwrite: bool = False) -> Path:
    out_dir.mkdir(parents=True, exist_ok=True)
    final_path = out_dir / Path(result.path).name

    if not result.split:
        download_file(result.url, final_path, overwrite=overwrite)
        return final_path

    numbers = [part_number(part) for part in result.parts]
    if numbers != list(range(1, len(numbers) + 1)):
        raise ValueError(f"Split parts are not continuous: {numbers}")

    temp_parts: list[Path] = []
    for part in result.parts:
        part_path = out_dir / Path(part).name
        download_file(raw_url(part), part_path, overwrite=overwrite)
        temp_parts.append(part_path)

    if final_path.exists() and not overwrite:
        return final_path

    partial_final = final_path.with_name(final_path.name + ".part")
    with partial_final.open("wb") as merged:
        for part_path in temp_parts:
            with part_path.open("rb") as part_file:
                while True:
                    chunk = part_file.read(1024 * 1024)
                    if not chunk:
                        break
                    merged.write(chunk)
    partial_final.replace(final_path)

    for part_path in temp_parts:
        try:
            part_path.unlink()
        except OSError:
            pass
    return final_path


def print_results(results: list[Result], json_output: bool = False, explain: bool = False, profile: RequestProfile | None = None) -> None:
    if json_output:
        print(json.dumps([result.__dict__ | {"url": result.url, "split": result.split} for result in results], ensure_ascii=False, indent=2))
        return
    if explain and profile:
        details = []
        if profile.province:
            details.append(f"province={profile.province}")
        if profile.location:
            details.append(f"location={profile.location}")
        if profile.stage:
            details.append(f"stage={profile.stage}")
        if profile.subject:
            details.append(f"subject={profile.subject}")
        if profile.explicit_versions:
            details.append(f"explicit_versions={','.join(profile.explicit_versions)}")
        if details:
            print("detected: " + "; ".join(details))
    for index, result in enumerate(results, 1):
        split = " split" if result.split else ""
        print(f"{index}. {result.path}{split}")
        print(f"   {result.url}")
        if explain and result.reasons:
            print(f"   why: {'; '.join(result.reasons)}")


def command_search(args: argparse.Namespace) -> int:
    query = " ".join(args.query)
    effective_query, context_notes = build_effective_query(query, cover_image=args.cover_image, ocr_text=args.ocr_text)
    profile = extract_profile(effective_query, province_override=args.province)
    try:
        results = search(load_tree(args.refresh), effective_query, args.limit, province=args.province)
    except urllib.error.URLError as exc:
        print(f"GitHub request failed: {exc}", file=sys.stderr)
        return 1
    add_context_reasons(results, context_notes)
    print_results(results, json_output=args.json, explain=args.explain, profile=profile)
    return 0 if results else 1


def command_download(args: argparse.Namespace) -> int:
    query = " ".join(args.query)
    effective_query, context_notes = build_effective_query(query, cover_image=args.cover_image, ocr_text=args.ocr_text)
    profile = extract_profile(effective_query, province_override=args.province)
    tokens = query_tokens(effective_query, profile)
    try:
        results = search(load_tree(args.refresh), effective_query, args.limit, province=args.province)
    except urllib.error.URLError as exc:
        print(f"GitHub request failed: {exc}", file=sys.stderr)
        return 1
    add_context_reasons(results, context_notes)

    if not results:
        print("No matching textbook found.", file=sys.stderr)
        return 1

    if args.pick:
        if args.pick < 1 or args.pick > len(results):
            print(f"--pick must be between 1 and {len(results)}.", file=sys.stderr)
            return 2
        result = results[args.pick - 1]
    elif args.auto:
        if not confidence_ok(results, tokens):
            print_results(results, explain=True, profile=profile)
            print("No confident single match. Re-run with --pick N after choosing.", file=sys.stderr)
            return 2
        result = results[0]
    elif args.first or len(results) == 1:
        result = results[0]
    else:
        print_results(results, explain=args.explain, profile=profile)
        print("Multiple matches found. Re-run with --pick N or --first.", file=sys.stderr)
        return 2

    try:
        path = download_result(result, Path(args.out).expanduser(), overwrite=args.overwrite)
    except (urllib.error.URLError, ValueError) as exc:
        print(f"Download failed: {exc}", file=sys.stderr)
        return 1

    print(json.dumps({"file": str(path), "source_path": result.path, "source_url": result.url, "split": result.split, "reasons": result.reasons}, ensure_ascii=False, indent=2))
    return 0


def command_self_test(_: argparse.Namespace) -> int:
    fake_paths = [
        "小学/语文/统编版/义务教育教科书·语文三年级上册.pdf",
        "小学/语文·书法练习指导/人美版/义务教育三至六年级·书法练习指导（实验）三年级上册.pdf",
        "初中/数学/苏教版-江苏凤凰科学技术出版社/义务教育教科书·数学七年级上册.pdf",
        "初中/数学/人教版-人民教育出版社/义务教育教科书·数学七年级上册.pdf",
        "初中/数学/北师大版-北京师范大学出版社/义务教育教科书·数学七年级上册.pdf",
        "初中/物理/人教版-人民教育出版社/义务教育教科书·物理八年级下册.pdf.1",
        "初中/物理/人教版-人民教育出版社/义务教育教科书·物理八年级下册.pdf.2",
        "初中/物理/北师大版-北京师范大学出版社/九年级/义务教育教科书·物理九年级全一册.pdf_merge_folder/义务教育教科书·物理九年级全一册.pdf.1",
        "初中/物理/北师大版-北京师范大学出版社/九年级/义务教育教科书·物理九年级全一册.pdf_merge_folder/义务教育教科书·物理九年级全一册.pdf.2",
        "大学/数学/高等数学/高等数学 同济第七版 上册.pdf",
        "大学/概率论/概率论与数理统计(浙大四版).pdf",
        "大学/线性代数/同济大学《线性代数》（第五版）教材电子版.pdf",
        "大学/高等数学/同济大学高等数学第七版/高等数学 第7版 上册 同济大学.pdf.1",
        "大学/高等数学/同济大学高等数学第七版/高等数学 第7版 上册 同济大学.pdf.2",
        "大学/离散数学/离散数学及其应用（英文第七版）Discrete Mathematics and Its Applications 7th Edition 2011.pdf",
        "大学/离散数学/[离散数学及其应用（英文第六版）].Discrete.Mathematics.and.its.Applications.djvu",
    ]
    assert set(query_tokens("帮我下载人教版初二物理下册教材")) == {"人教版", "八年级", "物理", "下册"}
    assert set(query_tokens("新版译林九上教材")) >= {"译林版", "新版", "九年级", "上册"}
    assert set(query_tokens("初三上译林英语")) >= {"九年级", "上册", "译林版", "英语"}
    assert set(query_tokens("九年级上译林英语")) >= {"九年级", "上册", "译林版", "英语"}
    assert set(query_tokens("本科线代教材")) >= {"大学", "线性代数"}
    assert set(query_tokens("大一高数上")) >= {"大学", "高等数学", "上册"}
    assert set(query_tokens("大二线代同济第五版")) >= {"大学", "线性代数", "同济", "第五版"}
    assert set(query_tokens("大三概率论浙大第四版")) >= {"大学", "概率论", "浙大", "四版"}
    assert set(query_tokens("离散原书第六版")) >= {"离散数学", "原书", "第六版"}
    assert set(query_tokens("数统浙大四版")) >= {"概率论与数理统计", "浙大", "四版"}
    assert "一年级" not in query_tokens("大一高数上册")
    assert extract_profile("安徽合肥三年级语文上册").province == "安徽"
    assert extract_profile("新版译林九上英语").stage == "初中"
    assert extract_profile("本科线代").stage == "大学"
    assert set(query_tokens("安徽合肥三年级语文上册")) == {"三年级", "语文", "上册"}
    assert search(fake_paths, "小学 三年级 语文 上册", 5)[0].path.endswith("语文三年级上册.pdf")
    assert search(fake_paths, "安徽 合肥 小学 三年级 语文 上册", 5)[0].path.startswith("小学/语文/统编版")
    assert "苏教版" in search(fake_paths, "江苏 南京 七年级 数学 上册", 5)[0].path
    assert "人教版" in search(fake_paths, "江苏 人教版 七年级 数学 上册", 5)[0].path
    assert "北师大版" in search(fake_paths, "广东 深圳 七年级 数学 上册", 5)[0].path
    assert confidence_ok(search(fake_paths, "安徽 合肥 小学 三年级 语文 上册", 5), ["小学", "三年级", "语文", "上册"])
    physics = search(fake_paths, "初二 物理 下册 人教版", 5)[0]
    assert physics.split and len(physics.parts) == 2
    merge_folder = search(fake_paths, "九年级 物理 北师大", 5)[0]
    assert merge_folder.path.endswith("义务教育教科书·物理九年级全一册.pdf")
    assert merge_folder.split and merge_folder.url.endswith(".pdf.1")
    assert search(fake_paths, "高等数学 上册", 5)[0].path.startswith("大学/")
    high_math = search(fake_paths, "本科 同济 高数 第7版 上册", 5)[0]
    assert "第7版" in high_math.path or "第七版" in high_math.path
    assert "概率论与数理统计" in search(fake_paths, "大学 概率论 浙大 第四版", 5)[0].path
    near_miss_tokens = query_tokens("大学 线性代数 同济 第六版")
    assert search(fake_paths, "大学 线性代数 同济 第六版", 5)[0].matched < len(near_miss_tokens)
    assert search(fake_paths, "大学 离散数学 英文 第六版", 5)[0].path.endswith(".djvu")
    effective, notes = build_effective_query("图片里的教材", ocr_text="新版译林 九上教材.pdf\n目录 播放演示\nKnow yourself")
    assert "新版译林" in effective and "目录" not in effective and notes == ["supplied cover text clues"]
    print("self-test passed")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Search and download public PDFs from TapXWorld/ChinaTextbook.")
    subparsers = parser.add_subparsers(required=True)

    search_parser = subparsers.add_parser("search", help="Search textbooks by natural-language keywords.")
    search_parser.add_argument("query", nargs="+")
    search_parser.add_argument("--limit", type=int, default=10)
    search_parser.add_argument("--refresh", action="store_true")
    search_parser.add_argument("--json", action="store_true")
    search_parser.add_argument("--province", help="Override or supply the province when it is not in the query.")
    search_parser.add_argument("--cover-image", help="Use OCR from a cover/page screenshot as extra matching clues.")
    search_parser.add_argument("--ocr-text", help="Use already-extracted cover/page text as extra matching clues.")
    search_parser.add_argument("--explain", action="store_true", help="Show why each candidate was ranked.")
    search_parser.set_defaults(func=command_search)

    download_parser = subparsers.add_parser("download", help="Download one matching textbook.")
    download_parser.add_argument("query", nargs="+")
    download_parser.add_argument("--out", default=str(DEFAULT_OUT))
    download_parser.add_argument("--limit", type=int, default=10)
    download_parser.add_argument("--pick", type=int)
    download_parser.add_argument("--first", action="store_true")
    download_parser.add_argument("--auto", action="store_true", help="Download the top result only when the score gap is confident; otherwise list candidates.")
    download_parser.add_argument("--overwrite", action="store_true")
    download_parser.add_argument("--refresh", action="store_true")
    download_parser.add_argument("--province", help="Override or supply the province when it is not in the query.")
    download_parser.add_argument("--cover-image", help="Use OCR from a cover/page screenshot as extra matching clues.")
    download_parser.add_argument("--ocr-text", help="Use already-extracted cover/page text as extra matching clues.")
    download_parser.add_argument("--explain", action="store_true", help="Show ranking reasons when multiple candidates need confirmation.")
    download_parser.set_defaults(func=command_download)

    self_test_parser = subparsers.add_parser("self-test", help="Run local assertions without network access.")
    self_test_parser.set_defaults(func=command_self_test)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
