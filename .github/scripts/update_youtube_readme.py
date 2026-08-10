#!/usr/bin/env python3
"""Split Worth Knowing TV RSS into long-form vs Shorts README sections."""

from __future__ import annotations

import re
import urllib.request
import xml.etree.ElementTree as ET
from datetime import datetime
from pathlib import Path

CHANNEL_FEED = (
    "https://www.youtube.com/feeds/videos.xml"
    "?channel_id=UCfz9mdRrU1xabf44sstW8Cg"
)
README_PATH = Path("README.md")
MAX_EACH = 4

NS = {
    "atom": "http://www.w3.org/2005/Atom",
    "yt": "http://www.youtube.com/xml/schemas/2015",
}


def fetch_entries() -> list[dict[str, str]]:
    with urllib.request.urlopen(CHANNEL_FEED, timeout=30) as response:
        root = ET.fromstring(response.read())

    entries: list[dict[str, str]] = []
    for entry in root.findall("atom:entry", NS):
        title = (entry.findtext("atom:title", default="", namespaces=NS) or "").strip()
        link_el = entry.find("atom:link", NS)
        url = link_el.attrib.get("href", "") if link_el is not None else ""
        video_id = entry.findtext("yt:videoId", default="", namespaces=NS) or ""
        published = entry.findtext("atom:published", default="", namespaces=NS) or ""
        if not title or not url or not video_id:
            continue
        entries.append(
            {
                "title": title,
                "url": url,
                "video_id": video_id,
                "published": published,
                "is_short": "/shorts/" in url,
            }
        )
    return entries


def format_date(published: str) -> str:
    try:
        dt = datetime.fromisoformat(published.replace("Z", "+00:00"))
        return f"{dt.strftime('%b')} {dt.day}, {dt.year}"
    except ValueError:
        return published[:10]


def render_rows(items: list[dict[str, str]], thumb_width: int) -> str:
    if not items:
        return "_Nothing here yet — check back soon._\n"

    blocks: list[str] = []
    for item in items:
        safe_title = (
            item["title"]
            .replace("&", "&amp;")
            .replace("<", "&lt;")
            .replace(">", "&gt;")
            .replace('"', "&quot;")
        )
        thumb = f"https://i.ytimg.com/vi/{item['video_id']}/mqdefault.jpg"
        date = format_date(item["published"])
        blocks.append(
            "<table><tr>"
            f'<td><a href="{item["url"]}">'
            f'<img width="{thumb_width}px" src="{thumb}" alt="{safe_title}"/>'
            "</a></td>\n"
            f'<td><a href="{item["url"]}">{safe_title}</a><br/>{date}</td>'
            "</tr></table>"
        )
    return "\n".join(blocks) + "\n"


def replace_section(readme: str, tag: str, body: str) -> str:
    pattern = re.compile(
        rf"(<!-- {tag}:START -->)(.*?)(<!-- {tag}:END -->)",
        re.DOTALL,
    )
    replacement = rf"\1\n{body}\3"
    updated, count = pattern.subn(replacement, readme)
    if count != 1:
        raise SystemExit(f"Expected exactly one {tag} section, found {count}")
    return updated


def main() -> None:
    entries = fetch_entries()
    long_form = [e for e in entries if not e["is_short"]][:MAX_EACH]
    shorts = [e for e in entries if e["is_short"]][:MAX_EACH]

    readme = README_PATH.read_text(encoding="utf-8")
    # Drop legacy single-list markers if present.
    readme = re.sub(
        r"<!-- YOUTUBE-LIST:START -->.*?<!-- YOUTUBE-LIST:END -->\n?",
        "",
        readme,
        flags=re.DOTALL,
    )
    readme = replace_section(readme, "YOUTUBE-LONG", render_rows(long_form, 180))
    readme = replace_section(readme, "YOUTUBE-SHORTS", render_rows(shorts, 140))
    README_PATH.write_text(readme, encoding="utf-8")
    print(f"Updated README: {len(long_form)} long-form, {len(shorts)} Shorts")


if __name__ == "__main__":
    main()
