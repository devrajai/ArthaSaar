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

export default {
  async fetch(request, env, ctx) {
    const url = new URL(request.url);

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
