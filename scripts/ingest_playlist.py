#!/usr/bin/env python3
"""
Ingest a YouTube playlist OR channel into the brain — "train the brain" with one link.

Usage (run from sandbox or anywhere with internet):
    python scripts/ingest_playlist.py "PLAYLIST_OR_CHANNEL_URL" ["section_name"]

Examples:
    python scripts/ingest_playlist.py \
      "https://youtube.com/playlist?list=PLyEvUpwXRAdPUT7VpaVblOxAVxAdGwmWU" \
      inspiring_traders
    python scripts/ingest_playlist.py "https://www.youtube.com/@AbhishekKar" abhishek_kar_channel

How it works (100% free, no API key):
  1. Detects playlist (?list=...) vs channel (/@handle or /channel/UC...)
  2. Fetches the page with a consent cookie + desktop UA
  3. Extracts every videoId via regex from ytInitialData (plain regex is robust
     against YouTube's ever-changing render structures: lockupViewModel,
     richItemRenderer, gridVideoRenderer all carry "videoId")
  4. Fetches each video's title + channel via YouTube oEmbed (works from
     datacenter IPs, ~3 req/sec is safe)
  5. Prints a JSON array [{title, by, url}] — merge into data/education.json
     under the given section, then commit

Limits: PUBLIC playlists/channels only. Playlist page loads ALL its videos;
channel /videos page loads the FIRST ~30 — for a full deep crawl of a huge
channel, pagination via continuation tokens is needed (future enhancement).
"""
import json
import re
import sys
import time
from urllib.request import Request, urlopen

UA = ("Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/124.0 Safari/537.36")


def get(url, cookie=None):
    headers = {"User-Agent": UA, "Accept-Language": "en-US,en;q=0.9"}
    if cookie:
        headers["Cookie"] = cookie
    req = Request(url, headers=headers)
    with urlopen(req, timeout=30) as r:
        return r.read().decode("utf-8", "replace")


def fetch_ids(url):
    """Returns (kind, page_url, ids)."""
    m = re.search(r"list=([\w-]+)", url)
    if m:
        page = f"https://www.youtube.com/playlist?list={m.group(1)}"
        kind = "playlist"
    elif "/@" in url or "/channel/" in url or "/c/" in url or "/user/" in url:
        base = url.split("?")[0].rstrip("/")
        page = base + "/videos"
        kind = "channel"
    else:
        print("ERROR: not a playlist or channel URL")
        sys.exit(1)
    html = get(page, cookie="CONSENT=YES+1")
    title_m = re.search(r"<title>(.*?)</title>", html)
    print(f"{kind} page: {title_m.group(1) if title_m else page}")
    ids = []
    for i in re.findall(r'"videoId":"([\w-]{11})"', html):
        if i not in ids:
            ids.append(i)
    print(f"videos found: {len(ids)}"
          + ("  (first page only — ~30 max for channels)" if kind == "channel" else ""))
    return kind, page, ids


def oembed(vid):
    try:
        j = json.loads(get(
            f"https://www.youtube.com/oembed?url="
            f"https://www.youtube.com/watch?v={vid}&format=json"))
        return j.get("title", ""), j.get("author_name", "")
    except Exception:  # noqa: BLE001
        return "", ""


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)
    url = sys.argv[1]
    section = sys.argv[2] if len(sys.argv) > 2 else "playlist"
    kind, page, ids = fetch_ids(url)
    out = []
    for n, vid in enumerate(ids, 1):
        t, ch = oembed(vid)
        if t:
            e = {"title": t, "url": f"https://youtu.be/{vid}"}
            if ch:
                e["by"] = ch
            out.append(e)
            print(f"  [{n}/{len(ids)}] {t[:60]} — {ch}")
        time.sleep(0.35)
    print(f"\n{json.dumps({'section': section, 'videos': out}, "
          f"ensure_ascii=False, indent=1)}")
    print(f"\n# merge the above into data/education.json under '{section}' and commit")


if __name__ == "__main__":
    main()
