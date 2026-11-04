/**
 * ArthaSaar live-data proxy (Cloudflare Worker, free tier).
 *
 * WHY THIS EXISTS
 *   Yahoo's chart API has no Access-Control-Allow-Origin header, so a browser page
 *   cannot read it directly - CORS blocks it. Verified: the response carries
 *   cache-control but no CORS header. This worker fetches Yahoo server-side and adds
 *   the CORS header, which is what lets the terminal draw live 1-minute candles.
 *
 * MEASURED, not assumed (NSE, during market hours):
 *   1m  -> ~3s median lag across 9 symbols, 7 days of history (1mo returns HTTP 422)
 *   5m / 15m / 30m -> 60 days    60m -> 2 years    1d -> years
 *   Yahoo itself caches for 10 seconds, so that is the real floor on freshness.
 *
 * SAFETY
 *   It is NOT an open proxy. Symbols, intervals and ranges are validated against a
 *   whitelist, so it cannot be used to fetch arbitrary URLs. Set a TOKEN secret and
 *   the worker will refuse requests without it.
 *
 * DEPLOY: see worker/README.md
 */

const ALLOWED_INTERVALS = new Set(["1m", "2m", "5m", "15m", "30m", "60m", "1h", "1d", "1wk", "1mo"]);
const ALLOWED_RANGES = new Set(["1d", "5d", "7d", "1mo", "3mo", "6mo", "1y", "2y", "5y", "10y", "ytd", "max"]);
// Yahoo tickers: letters, digits, and . ^ = - _  (RELIANCE.NS, ^NSEI, BTC-USD, EURINR=X)
const SYMBOL_RE = /^[A-Za-z0-9.^=_-]{1,24}$/;

// How long Cloudflare should hold each response. Matches Yahoo's own 10s cache for
// intraday; daily bars change rarely so they can sit longer.
function ttlFor(interval) {
  if (interval === "1m") return 10;
  if (interval === "2m" || interval === "5m") return 30;
  if (interval === "15m" || interval === "30m") return 60;
  if (interval === "60m" || interval === "1h") return 120;
  return 600;
}

function cors(res, origin) {
  const h = new Headers(res.headers);
  h.set("Access-Control-Allow-Origin", origin || "*");
  h.set("Access-Control-Allow-Methods", "GET, OPTIONS");
  h.set("Access-Control-Allow-Headers", "Content-Type, X-Token");
  h.set("Access-Control-Max-Age", "86400");
  h.set("Vary", "Origin");
  return new Response(res.body, { status: res.status, headers: h });
}

function json(obj, status) {
  return new Response(JSON.stringify(obj), {
    status: status || 200,
    headers: { "Content-Type": "application/json", "Cache-Control": "no-store" },
  });
}


/* ------------------------------------------------------------------------------------
   YOUTUBE UPLOAD WEBHOOK  (PubSubHubbub)

   WHY: the nightly pipeline runs at 23:00 IST, so a video published at 10:00 waits 13 hours.
   YouTube's RSS feed has no push notification, but PubSubHubbub does: subscribe to a
   channel's topic URL and the hub POSTs to us within seconds of a new upload.

   Two things must work here:
     GET   the hub's verification challenge - it sends hub.challenge and we must echo the
           exact value back with a 200, or the subscription is never created
     POST  the actual notification, an Atom XML body

   SECURITY: PubSubHubbub bodies are unsigned unless hub.secret is set at subscribe time.
   We set one, so every POST carries X-Hub-Signature: sha1=<hmac>. Without verifying it,
   anyone who learns this URL could trigger workflow runs. Verification is HMAC-SHA1 over
   the RAW body - it must be read before any parsing.
   ------------------------------------------------------------------------------------ */

async function hmacSha1Hex(secret, bodyBytes) {
  const key = await crypto.subtle.importKey(
    "raw", new TextEncoder().encode(secret),
    { name: "HMAC", hash: "SHA-1" }, false, ["sign"]);
  const sig = await crypto.subtle.sign("HMAC", key, bodyBytes);
  return [...new Uint8Array(sig)].map(b => b.toString(16).padStart(2, "0")).join("");
}

async function youtubeHook(request, env) {
  const url = new URL(request.url);

  // ---- verification -------------------------------------------------------------
  if (request.method === "GET") {
    const mode = url.searchParams.get("hub.mode");
    const challenge = url.searchParams.get("hub.challenge");
    const topic = url.searchParams.get("hub.topic") || "";
    if (mode && challenge) {
      // Only accept subscriptions aimed at a YouTube feed, so this cannot be used to
      // register us for arbitrary third-party notifications.
      if (!topic.includes("youtube.com/xml/feeds/videos.xml")) {
        return new Response("bad topic", { status: 400 });
      }
      console.log("youtube-hook verify:", mode, topic.slice(0, 90));
      return new Response(challenge, { status: 200, headers: { "Content-Type": "text/plain" } });
    }
    return new Response("youtube hook ready", { status: 200 });
  }

  if (request.method !== "POST") return new Response("POST only", { status: 405 });

  // ---- signature ----------------------------------------------------------------
  const raw = await request.arrayBuffer();
  const secret = env && env.YT_HUB_SECRET;
  if (secret) {
    const sent = (request.headers.get("X-Hub-Signature") || "").replace(/^sha1=/, "").toLowerCase();
    const want = await hmacSha1Hex(secret, raw);
    if (sent !== want) {
      console.log("youtube-hook: bad signature");
      return new Response("bad signature", { status: 401 });
    }
  } else {
    console.log("youtube-hook: YT_HUB_SECRET not set - accepting unverified POST");
  }

  const body = new TextDecoder().decode(raw);

  // ---- what arrived -------------------------------------------------------------
  // Scope to the <entry> block first. The feed itself also carries a <title> - the channel
  // name - and matching the whole body picks that up instead of the video title. Caught by
  // testing against a real Atom body, where the title came back as "Groww Edge".
  const entry = (body.match(/<entry>([\s\S]*?)<\/entry>/) || [])[1] || body;
  const videoId = (entry.match(/<yt:videoId>([^<]+)<\/yt:videoId>/) || [])[1] || "";
  const channelId = (entry.match(/<yt:channelId>([^<]+)<\/yt:channelId>/) || [])[1] || "";
  const title = (entry.match(/<title[^>]*>([^<]*)<\/title>/) || [])[1] || "";

  // The hub can send the same video more than once. Remember recent ids at the edge so
  // one upload cannot queue several workflow runs.
  const cache = caches.default;
  const seenKey = new Request("https://arthasaar.internal/yt-seen/" + (videoId || "unknown"), { method: "GET" });
  if (videoId && await cache.match(seenKey)) {
    console.log("youtube-hook: duplicate", videoId);
    return new Response("duplicate", { status: 200 });
  }

  // ---- fire the workflow --------------------------------------------------------
  const token = env && env.GITHUB_DISPATCH_TOKEN;
  const repo = (env && env.DISPATCH_REPO) || "devrajai/ArthaSaar";
  if (!token) {
    console.log("youtube-hook: GITHUB_DISPATCH_TOKEN missing - nothing dispatched");
    return new Response("no token configured", { status: 500 });
  }

  const res = await fetch("https://api.github.com/repos/" + repo + "/dispatches", {
    method: "POST",
    headers: {
      "Authorization": "Bearer " + token,
      "Accept": "application/vnd.github+json",
      "User-Agent": "ArthaSaar-YouTube-Hook",
      "Content-Type": "application/json",
    },
    body: JSON.stringify({
      event_type: "youtube-upload",
      client_payload: { video_id: videoId, channel_id: channelId, title: title.slice(0, 200) },
    }),
  });

  if (!res.ok) {
    const detail = await res.text();
    console.log("youtube-hook: dispatch failed", res.status, detail.slice(0, 200));
    return new Response("dispatch failed", { status: 502 });
  }

  if (videoId) {
    await cache.put(seenKey, new Response("1", { headers: { "Cache-Control": "max-age=3600" } }));
  }
  console.log("youtube-hook: dispatched", videoId, title.slice(0, 60));
  return new Response("ok", { status: 200 });
}

export default {
  async fetch(request, env, ctx) {
    const url = new URL(request.url);

    // The YouTube webhook must be handled before the GET-only guard below, because the
    // hub sends a POST and the verification is a GET with a challenge parameter.
    if (url.pathname === "/youtube-hook") {
      try {
        return await youtubeHook(request, env);
      } catch (e) {
        console.log("youtube-hook error", String(e).slice(0, 200));
        return new Response("hook error", { status: 500 });
      }
    }

    if (request.method === "OPTIONS") return cors(new Response(null, { status: 204 }));
    if (request.method !== "GET") return cors(json({ error: "GET only" }, 405));

    // A simple shared secret so this is not a free public proxy. Optional: if TOKEN
    // is unset the worker runs open, which is fine for a personal terminal but means
    // anyone who knows the URL can use it.
    if (env && env.TOKEN) {
      const sent = request.headers.get("X-Token") || url.searchParams.get("token");
      if (sent !== env.TOKEN) return cors(json({ error: "unauthorised" }, 401));
    }

    const symbol = (url.searchParams.get("symbol") || "").trim();
    const interval = (url.searchParams.get("interval") || "1d").trim();
    const range = (url.searchParams.get("range") || "1d").trim();

    if (!SYMBOL_RE.test(symbol)) return cors(json({ error: "bad symbol" }, 400));
    if (!ALLOWED_INTERVALS.has(interval)) return cors(json({ error: "bad interval" }, 400));
    if (!ALLOWED_RANGES.has(range)) return cors(json({ error: "bad range" }, 400));

    // Yahoo rejects 1-minute requests beyond 7 days; fail clearly instead of passing
    // the 422 through, so the client can show a sensible message.
    if (interval === "1m" && !["1d", "5d", "7d"].includes(range)) {
      return cors(json({ error: "1m data is limited to 7 days" }, 400));
    }

    const target = "https://query1.finance.yahoo.com/v8/finance/chart/" +
      encodeURIComponent(symbol) +
      "?interval=" + encodeURIComponent(interval) +
      "&range=" + encodeURIComponent(range) +
      "&includePrePost=false";

    // Cloudflare edge cache - keeps us well inside any rate limit and makes repeat
    // loads instant. Keyed on the full query so different timeframes cache separately.
    const cache = caches.default;
    const cacheKey = new Request(url.toString(), { method: "GET" });
    let hit = await cache.match(cacheKey);
    if (hit) {
      const r = new Response(hit.body, hit);
      r.headers.set("X-Cache", "HIT");
      return cors(r);
    }

    let upstream;
    try {
      upstream = await fetch(target, {
        headers: {
          "User-Agent": "Mozilla/5.0 (compatible; ArthaSaar/1.0)",
          "Accept": "application/json",
        },
      });
    } catch (e) {
      return cors(json({ error: "upstream fetch failed", detail: String(e).slice(0, 120) }, 502));
    }

    if (!upstream.ok) {
      return cors(json({ error: "upstream " + upstream.status }, upstream.status === 404 ? 404 : 502));
    }

    const body = await upstream.text();
    const res = new Response(body, {
      status: 200,
      headers: {
        "Content-Type": "application/json; charset=utf-8",
        "Cache-Control": "public, max-age=" + ttlFor(interval),
        "X-Cache": "MISS",
      },
    });

    // Store in the edge cache without blocking the response.
    ctx.waitUntil(cache.put(cacheKey, res.clone()));
    return cors(res);
  },
};
