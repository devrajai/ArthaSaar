"""
youtube_source.py - poll a YouTube channel's uploads via its public Atom feed.

    https://www.youtube.com/feeds/videos.xml?channel_id=<UC...>

No API key, no login, no quota. The feed returns the channel's ~15 most recent
uploads - which is exactly what a "what's new" trigger needs. Counting a channel's
ENTIRE back-catalogue needs the YouTube Data API (free key), which this does not use.

Finding a channel_id from a handle: fetch https://www.youtube.com/@<handle> and read
the "externalId" field - NOT the first "channelId" you find, which can belong to a
related channel embedded in the page.
"""

from __future__ import annotations

import xml.etree.ElementTree as ET
from dataclasses import dataclass, asdict

import requests

FEED = "https://www.youtube.com/feeds/videos.xml?channel_id={cid}"

NS = {
    "a": "http://www.w3.org/2005/Atom",
    "yt": "http://www.youtube.com/xml/schemas/2015",
    "media": "http://search.yahoo.com/mrss/",
}

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/124.0 Safari/537.36"
    ),
    "Accept-Language": "en-US,en;q=0.9",
}


@dataclass
class Video:
    video_id: str
    channel_id: str
    channel_name: str
    title: str
    published: str
    updated: str
    url: str
    thumbnail: str
    views: str
    description: str


def _text(node, path, default=""):
    el = node.find(path, NS)
    return el.text if el is not None and el.text else default


RETRY_STATUS = {404, 429, 500, 502, 503, 504}


def fetch_channel(channel_id: str, *, timeout: int = 30,
                  retries: int = 3) -> tuple[str, list[Video]]:
    """Return (channel_title, [Video, ...]) for a channel_id.

    Retries on throttling. YouTube answers an existing channel with 404/5xx when it is
    rate-limiting rather than saying so - which matters a lot for an hourly poll.
    """
    import time as _t
    last = None
    for attempt in range(1, retries + 1):
        try:
            r = requests.get(FEED.format(cid=channel_id), headers=HEADERS, timeout=timeout)
            if r.status_code in RETRY_STATUS and attempt < retries:
                _t.sleep(2 * attempt)
                last = f"HTTP {r.status_code}"
                continue
            r.raise_for_status()
            root = ET.fromstring(r.content)
            break
        except requests.RequestException as e:  # noqa: PERF203
            last = f"{type(e).__name__}"
            if attempt >= retries:
                raise
            _t.sleep(2 * attempt)
    else:
        raise RuntimeError(f"feed unavailable after {retries} attempts ({last})")
    channel_title = _text(root, "a:title", channel_id)

    videos: list[Video] = []
    for e in root.findall("a:entry", NS):
        vid = _text(e, "yt:videoId")
        if not vid:
            continue
        link = e.find("a:link[@rel='alternate']", NS)
        thumb = e.find("media:group/media:thumbnail", NS)
        # views sits inside media:group/media:community/media:statistics
        stats = e.find(".//media:statistics", NS)
        videos.append(Video(
            video_id=vid,
            channel_id=channel_id,
            channel_name=channel_title,
            title=_text(e, "a:title"),
            published=_text(e, "a:published"),
            updated=_text(e, "a:updated"),
            url=link.get("href") if link is not None else f"https://www.youtube.com/watch?v={vid}",
            thumbnail=thumb.get("url") if thumb is not None else "",
            views=stats.get("views") if stats is not None else "",
            description=_text(e, "media:group/media:description")[:500],
        ))
    return channel_title, videos


def as_dicts(videos: list[Video]) -> list[dict]:
    return [asdict(v) for v in videos]
