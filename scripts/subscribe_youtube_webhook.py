#!/usr/bin/env python3
"""Subscribe every YouTube channel to the PubSubHubbub hub, pointed at our Worker.

WHY THIS IS NEEDED
YouTube has no webhook you can register in a dashboard. What it does have is PubSubHubbub
(WebSub): you POST a subscription to a hub, the hub verifies your callback with a GET
challenge, and from then on it POSTs every new upload to you within seconds.

Without this, the pipeline only learns about a video at 23:00 IST. With it, an upload at
10:00 is collected within a minute.

LEASES EXPIRE
A subscription is not permanent. The hub grants a lease (we ask for 5 days) and then stops
delivering unless you renew. That is why this runs on a schedule rather than once - a silent
expiry is exactly the failure that looks like "the webhook stopped working".

VERIFY=SYNC
We ask the hub to verify immediately, so this script learns straight away whether the Worker
answered the challenge correctly. With verify=async the POST would return 202 and any problem
would surface only as missing notifications days later.

ENVIRONMENT
  YT_HUB_CALLBACK   full URL of the Worker route, e.g.
                    https://arthasaar-proxy.<account>.workers.dev/youtube-hook
  YT_HUB_SECRET     shared secret; the hub signs every POST with it and the Worker checks
"""
import json, os, sys, time, urllib.parse, urllib.request

HUB = "https://pubsubhubbub.appspot.com/subscribe"
TOPIC = "https://www.youtube.com/xml/feeds/videos.xml?channel_id=%s"
CHANNELS = "config/channels.json"
LEASE = 432000          # 5 days; the renewal job runs weekly so this always overlaps
UA = {"User-Agent": "ArthaSaar-YouTube-Subscriber/1.0"}


def post(fields):
    data = urllib.parse.urlencode(fields).encode()
    req = urllib.request.Request(HUB, data=data, headers=UA, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            return r.status, ""
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode("utf-8", "replace")[:160]
    except Exception as e:
        return 0, "%s: %s" % (type(e).__name__, str(e)[:120])


def main():
    callback = (os.environ.get("YT_HUB_CALLBACK") or "").strip()
    secret = (os.environ.get("YT_HUB_SECRET") or "").strip()

    if not callback or not callback.startswith("https://"):
        print("::error title=No callback::YT_HUB_CALLBACK must be the Worker URL, "
              "e.g. https://arthasaar-proxy.<account>.workers.dev/youtube-hook")
        return 1
    if not secret:
        print("::warning title=No secret::YT_HUB_SECRET is unset, so POSTs arrive unsigned "
              "and the Worker cannot verify them")

    try:
        channels = [c for c in json.load(open(CHANNELS))["channels"] if c.get("active", True)]
    except Exception as e:
        print("::error title=No channels::%s" % type(e).__name__)
        return 1

    print("subscribing %d channels -> %s" % (len(channels), callback))
    ok = failed = 0
    for c in channels:
        cid = c.get("channel_id")
        if not cid:
            continue
        fields = {
            "hub.mode": "subscribe",
            "hub.topic": TOPIC % cid,
            "hub.callback": callback,
            "hub.verify": "sync",
            "hub.lease_seconds": str(LEASE),
        }
        if secret:
            fields["hub.secret"] = secret
        status, detail = post(fields)
        # 202/204 = accepted and (with verify=sync) verified. 4xx means the challenge failed.
        if status in (200, 202, 204):
            ok += 1
            print("  %-28s subscribed (HTTP %s)" % (c.get("name", cid)[:28], status))
        else:
            failed += 1
            print("  %-28s FAILED (HTTP %s) %s" % (c.get("name", cid)[:28], status, detail))
        time.sleep(0.6)

    print("\n%d subscribed, %d failed" % (ok, failed))
    if failed:
        print("::warning title=%d subscriptions failed::a 4xx usually means the Worker did not "
              "echo hub.challenge - check the /youtube-hook GET route" % failed)
    return 0


if __name__ == "__main__":
    sys.exit(main())
