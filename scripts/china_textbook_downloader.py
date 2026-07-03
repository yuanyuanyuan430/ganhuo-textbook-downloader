#!/usr/bin/env python3
"""Search and download PDFs from TapXWorld/ChinaTextbook."""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
import time
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
CACHE_PATH = Path(os.environ.get("XDG_CACHE_HOME", Path.home() / ".cache")) / "ganhuo-textbook-downloader" / "tree.json"
CACHE_TTL_SECONDS = 24 * 60 * 60
DEFAULT_OUT = Path.home() / "Downloads" / "ChinaTextbook"

ALIASES = {
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
}

KEYWORDS = [
    "选择性必修",
    "体育与健康",
    "道德与法治",
    "思想政治",
    "人民教育出版社",
    "高等数学",
    "线性代数",
    "离散数学",
    "概率论",
    "信息技术",
    "通用技术",
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
    "生物学",
    "高等数学",
    "线性代数",
    "离散数学",
    "概率论",
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
NON_TEXTBOOK_WORDS = ("练习", "习题", "教师", "教师用书", "活动手册", "书法练习")
VERSION_WORDS = ("统编版", "人教版", "人教A版", "北师大", "北师大版", "苏教版", "沪教版", "北京版", "浙教版", "粤教版", "译林版", "鲁教版", "鲁科版", "青岛版", "华东师大版", "外研版")

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
    subject: str | None = None
    explicit_versions: list[str] = field(default_factory=list)


def raw_url(path: str) -> str:
    return RAW_BASE + urllib.parse.quote(path, safe="/")


def normalize(text: str) -> str:
    text = text.lower()
    for old, new in ALIASES.items():
        text = text.replace(old.lower(), new.lower())
    return re.sub(r"[\s/_·・（）()【】\[\]《》<>:：,，.。、\-]+", "", text)


def extract_profile(query: str, province_override: str | None = None) -> RequestProfile:
    profile = RequestProfile()
    normalized = query

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
    normalized_query = query
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
        and re.search(r"\.pdf(\.\d+)?$", item.get("path", ""), re.IGNORECASE)
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
    profile = extract_profile(query, province_override=args.province)
    try:
        results = search(load_tree(args.refresh), query, args.limit, province=args.province)
    except urllib.error.URLError as exc:
        print(f"GitHub request failed: {exc}", file=sys.stderr)
        return 1
    print_results(results, json_output=args.json, explain=args.explain, profile=profile)
    return 0 if results else 1


def command_download(args: argparse.Namespace) -> int:
    query = " ".join(args.query)
    profile = extract_profile(query, province_override=args.province)
    tokens = query_tokens(query, profile)
    try:
        results = search(load_tree(args.refresh), query, args.limit, province=args.province)
    except urllib.error.URLError as exc:
        print(f"GitHub request failed: {exc}", file=sys.stderr)
        return 1

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
    ]
    assert set(query_tokens("帮我下载人教版初二物理下册教材")) == {"人教版", "八年级", "物理", "下册"}
    assert extract_profile("安徽合肥三年级语文上册").province == "安徽"
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
