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
from pathlib import Path

REPO = "TapXWorld/ChinaTextbook"
BRANCH = "master"
TREE_API = f"https://api.github.com/repos/{REPO}/git/trees/{BRANCH}?recursive=1"
RAW_BASE = f"https://raw.githubusercontent.com/{REPO}/{BRANCH}/"
CACHE_PATH = Path(os.environ.get("XDG_CACHE_HOME", Path.home() / ".cache")) / "china-textbook-downloader" / "tree.json"
CACHE_TTL_SECONDS = 24 * 60 * 60
DEFAULT_OUT = Path.home() / "Downloads" / "ChinaTextbook"

ALIASES = {
    "初一": "七年级",
    "初二": "八年级",
    "初三": "九年级",
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
    "统编版",
    "北师大",
    "苏教版",
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


@dataclass
class Result:
    path: str
    parts: list[str]
    score: int
    matched: int

    @property
    def split(self) -> bool:
        return len(self.parts) > 1 or self.parts[0] != self.path

    @property
    def url(self) -> str:
        return raw_url(self.path if not self.split else self.parts[0])


def raw_url(path: str) -> str:
    return RAW_BASE + urllib.parse.quote(path, safe="/")


def normalize(text: str) -> str:
    text = text.lower()
    for old, new in ALIASES.items():
        text = text.replace(old.lower(), new.lower())
    return re.sub(r"[\s/_·・（）()【】\[\]《》<>:：,，.。、\-]+", "", text)


def query_tokens(query: str) -> list[str]:
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


def fetch_json(url: str) -> dict:
    request = urllib.request.Request(url, headers={"User-Agent": "china-textbook-downloader-skill"})
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


def search(paths: list[str], query: str, limit: int) -> list[Result]:
    tokens = query_tokens(query)
    if not tokens:
        raise SystemExit("Please include grade, subject, version, or title keywords.")

    results: list[Result] = []
    for base, parts in group_pdf_parts(paths).items():
        haystack = normalize(base)
        matched = sum(1 for token in tokens if token in haystack)
        if matched == 0:
            continue
        score = matched * 100 - len(base)
        if matched == len(tokens):
            score += 1000
        results.append(Result(base, parts, score, matched))

    full_matches = [result for result in results if result.matched == len(tokens)]
    chosen = full_matches or results
    chosen.sort(key=lambda result: (-result.score, result.path))
    return chosen[:limit]


def download_file(url: str, destination: Path, overwrite: bool = False) -> None:
    if destination.exists() and not overwrite:
        return
    partial = destination.with_name(destination.name + ".part")
    request = urllib.request.Request(url, headers={"User-Agent": "china-textbook-downloader-skill"})
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


def print_results(results: list[Result], json_output: bool = False) -> None:
    if json_output:
        print(json.dumps([result.__dict__ | {"url": result.url, "split": result.split} for result in results], ensure_ascii=False, indent=2))
        return
    for index, result in enumerate(results, 1):
        split = " split" if result.split else ""
        print(f"{index}. {result.path}{split}")
        print(f"   {result.url}")


def command_search(args: argparse.Namespace) -> int:
    try:
        results = search(load_tree(args.refresh), " ".join(args.query), args.limit)
    except urllib.error.URLError as exc:
        print(f"GitHub request failed: {exc}", file=sys.stderr)
        return 1
    print_results(results, json_output=args.json)
    return 0 if results else 1


def command_download(args: argparse.Namespace) -> int:
    try:
        results = search(load_tree(args.refresh), " ".join(args.query), args.limit)
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
    elif args.first or len(results) == 1:
        result = results[0]
    else:
        print_results(results)
        print("Multiple matches found. Re-run with --pick N or --first.", file=sys.stderr)
        return 2

    try:
        path = download_result(result, Path(args.out).expanduser(), overwrite=args.overwrite)
    except (urllib.error.URLError, ValueError) as exc:
        print(f"Download failed: {exc}", file=sys.stderr)
        return 1

    print(json.dumps({"file": str(path), "source_path": result.path, "source_url": result.url, "split": result.split}, ensure_ascii=False, indent=2))
    return 0


def command_self_test(_: argparse.Namespace) -> int:
    fake_paths = [
        "小学/语文/统编版/义务教育教科书·语文三年级上册.pdf",
        "初中/物理/人教版-人民教育出版社/义务教育教科书·物理八年级下册.pdf.1",
        "初中/物理/人教版-人民教育出版社/义务教育教科书·物理八年级下册.pdf.2",
        "初中/物理/北师大版-北京师范大学出版社/九年级/义务教育教科书·物理九年级全一册.pdf_merge_folder/义务教育教科书·物理九年级全一册.pdf.1",
        "初中/物理/北师大版-北京师范大学出版社/九年级/义务教育教科书·物理九年级全一册.pdf_merge_folder/义务教育教科书·物理九年级全一册.pdf.2",
        "大学/数学/高等数学/高等数学 同济第七版 上册.pdf",
    ]
    assert set(query_tokens("帮我下载人教版初二物理下册教材")) == {"人教版", "八年级", "物理", "下册"}
    assert search(fake_paths, "小学 三年级 语文 上册", 5)[0].path.endswith("语文三年级上册.pdf")
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
    search_parser.set_defaults(func=command_search)

    download_parser = subparsers.add_parser("download", help="Download one matching textbook.")
    download_parser.add_argument("query", nargs="+")
    download_parser.add_argument("--out", default=str(DEFAULT_OUT))
    download_parser.add_argument("--limit", type=int, default=10)
    download_parser.add_argument("--pick", type=int)
    download_parser.add_argument("--first", action="store_true")
    download_parser.add_argument("--overwrite", action="store_true")
    download_parser.add_argument("--refresh", action="store_true")
    download_parser.set_defaults(func=command_download)

    self_test_parser = subparsers.add_parser("self-test", help="Run local assertions without network access.")
    self_test_parser.set_defaults(func=command_self_test)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
