#!/usr/bin/env python3
"""Poll free RSS mirrors for new X posts and notify a WeCom group."""

from __future__ import annotations

import html
import json
import os
import re
import sys
import urllib.error
import urllib.request
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from pathlib import Path


USERNAME = os.getenv("X_USERNAME", "thsottiaux").lstrip("@")
DEFAULT_FEEDS = (
    f"https://xcancel.com/{USERNAME}/rss",
    f"https://nitter.poast.org/{USERNAME}/rss",
    f"https://rsshub.app/twitter/user/{USERNAME}",
)
STATE_PATH = Path(os.getenv("STATE_PATH", "state/seen.json"))
USER_AGENT = "Mozilla/5.0 (compatible; x-to-wecom/1.0)"
ID_RE = re.compile(r"/status/(\d+)")
TAG_RE = re.compile(r"<[^>]+>")


@dataclass(frozen=True)
class Post:
    post_id: str
    text: str
    link: str


def feed_urls() -> list[str]:
    configured = os.getenv("FEED_URLS", "")
    if configured.strip():
        return [url.strip() for url in configured.split(",") if url.strip()]
    return list(DEFAULT_FEEDS)


def fetch(url: str) -> bytes:
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(request, timeout=25) as response:
        return response.read()


def clean_text(value: str) -> str:
    value = TAG_RE.sub(" ", value or "")
    value = html.unescape(value)
    return " ".join(value.split())


def child_text(element: ET.Element, names: tuple[str, ...]) -> str:
    for child in element:
        name = child.tag.rsplit("}", 1)[-1]
        if name in names and child.text:
            return child.text.strip()
    return ""


def parse_feed(data: bytes) -> list[Post]:
    data = data.lstrip()
    if data.startswith(b"\xef\xbb\xbf"):
        data = data[3:].lstrip()
    root = ET.fromstring(data)
    posts: list[Post] = []
    for item in root.iter():
        if item.tag.rsplit("}", 1)[-1] not in {"item", "entry"}:
            continue

        link = child_text(item, ("link",))
        if not link:
            for child in item:
                if child.tag.rsplit("}", 1)[-1] == "link":
                    link = child.attrib.get("href", "")
                    if link:
                        break
        guid = child_text(item, ("guid", "id"))
        match = ID_RE.search(link) or ID_RE.search(guid)
        if not match:
            continue

        title = child_text(item, ("title",))
        description = child_text(item, ("description", "summary", "content"))
        text = clean_text(title or description)
        posts.append(Post(match.group(1), text, f"https://x.com/{USERNAME}/status/{match.group(1)}"))
    return posts


def get_posts() -> tuple[list[Post], str]:
    errors: list[str] = []
    for url in feed_urls():
        try:
            posts = parse_feed(fetch(url))
            if posts:
                return posts, url
            errors.append(f"{url}: 没有找到帖子")
        except (OSError, urllib.error.URLError, ET.ParseError) as exc:
            errors.append(f"{url}: {exc}")
    raise RuntimeError("所有免费 RSS 源均不可用:\n" + "\n".join(errors))


def load_seen() -> set[str] | None:
    if not STATE_PATH.exists():
        return None
    try:
        data = json.loads(STATE_PATH.read_text(encoding="utf-8"))
        return {str(value) for value in data.get("seen", [])}
    except (OSError, ValueError, TypeError) as exc:
        raise RuntimeError(f"状态文件损坏: {exc}") from exc


def save_seen(ids: set[str]) -> None:
    STATE_PATH.parent.mkdir(parents=True, exist_ok=True)
    newest = sorted(ids, key=int, reverse=True)[:200]
    STATE_PATH.write_text(
        json.dumps({"seen": newest}, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def is_original(post: Post) -> bool:
    text = post.text.lstrip()
    return not text.startswith(("RT @", "R to @", "Replying to @"))


def send_wecom(post: Post, webhook: str) -> None:
    safe_text = post.text.replace("[", "［").replace("]", "］")[:1800]
    content = f"## @{USERNAME} 发布了新动态\n\n{safe_text}\n\n[点击查看原帖]({post.link})"
    body = json.dumps({"msgtype": "markdown", "markdown": {"content": content}}).encode()
    request = urllib.request.Request(
        webhook,
        data=body,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(request, timeout=20) as response:
        result = json.loads(response.read().decode("utf-8"))
    if result.get("errcode") != 0:
        raise RuntimeError(f"企业微信返回错误: {result}")


def main() -> int:
    posts, source = get_posts()
    posts = [post for post in posts if is_original(post)]
    current_ids = {post.post_id for post in posts}
    seen = load_seen()

    if seen is None:
        save_seen(current_ids)
        print(f"首次运行：已记录 {len(current_ids)} 条现有帖子，不发送历史消息。来源: {source}")
        return 0

    new_posts = [post for post in posts if post.post_id not in seen]
    new_posts.sort(key=lambda post: int(post.post_id))
    webhook = os.getenv("WECOM_WEBHOOK", "").strip()
    if new_posts and not webhook:
        raise RuntimeError("发现新帖子，但未设置 WECOM_WEBHOOK")

    for post in new_posts:
        send_wecom(post, webhook)
        print(f"已推送: {post.link}")

    save_seen(seen | current_ids)
    if not new_posts:
        print(f"没有新帖子。来源: {source}")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(f"错误: {exc}", file=sys.stderr)
        raise SystemExit(1)
