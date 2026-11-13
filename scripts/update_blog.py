"""네이버 블로그 RSS에서 특정 카테고리 글만 골라 README의 BLOG 구간을 갱신한다.

외부 패키지 없이 표준 라이브러리만 쓴다.
  python scripts/update_blog.py                     # RSS를 받아 README.md 갱신
  python scripts/update_blog.py --file sample.xml   # 저장된 RSS로 시험
"""
import argparse
import email.utils
import pathlib
import re
import sys
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET

BLOG_ID = "hundredhey"
CATEGORY = "SSAFY"          # 이 카테고리 글만 보여 준다 (일상 글 제외)
LIMIT = 3
README = pathlib.Path(__file__).resolve().parents[1] / "README.md"
START, END = "<!-- BLOG:START -->", "<!-- BLOG:END -->"


def fetch(url: str) -> bytes:
    req = urllib.request.Request(url, headers={"User-Agent": "profile-readme-blog-feed/1.0"})
    with urllib.request.urlopen(req, timeout=30) as resp:
        return resp.read()


def in_category(item: ET.Element) -> bool:
    for cat in item.findall("category"):
        name = (cat.text or "").strip()
        # "SSAFY" 또는 하위 카테고리 "SSAFY>..." 형태를 모두 허용
        if name == CATEGORY or name.startswith(CATEGORY + ">") or name.startswith(CATEGORY + "/"):
            return True
    return False


def clean_link(link: str) -> str:
    parts = urllib.parse.urlsplit(link.strip())
    return urllib.parse.urlunsplit((parts.scheme, parts.netloc, parts.path, "", ""))


def md_escape(text: str) -> str:
    return re.sub(r"([\\\[\]`*_<>])", r"\\\1", text.strip())


def build_lines(rss: bytes) -> list[str]:
    root = ET.fromstring(rss)
    lines = []
    for item in root.findall("./channel/item"):
        if not in_category(item):
            continue
        title = item.findtext("title") or ""
        link = clean_link(item.findtext("link") or "")
        date = ""
        if item.findtext("pubDate"):
            date = email.utils.parsedate_to_datetime(item.findtext("pubDate")).strftime("%Y.%m.%d")
        lines.append(f"- `{date}` [{md_escape(title)}]({link})")
        if len(lines) == LIMIT:
            break
    return lines


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--file", help="RSS를 내려받지 않고 이 파일을 읽는다")
    args = ap.parse_args()

    rss = pathlib.Path(args.file).read_bytes() if args.file else fetch(f"https://rss.blog.naver.com/{BLOG_ID}.xml")
    lines = build_lines(rss)
    if not lines:
        # 글을 못 찾았을 때 기존 목록을 지우지 않는다
        print(f"'{CATEGORY}' 카테고리 글을 찾지 못해 README를 그대로 둡니다.")
        return 0

    readme = README.read_text(encoding="utf-8")
    if START not in readme or END not in readme:
        print("README에 BLOG 표시가 없습니다.", file=sys.stderr)
        return 1
    head, rest = readme.split(START, 1)
    _, tail = rest.split(END, 1)
    new = head + START + "\n" + "\n".join(lines) + "\n" + END + tail
    if new != readme:
        README.write_text(new, encoding="utf-8")
        print("README를 갱신했습니다:\n" + "\n".join(lines))
    else:
        print("바뀐 글이 없습니다.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
