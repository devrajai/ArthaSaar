# Live-data proxy + real login (both free)

Two problems, one setup:

1. **Live 1-minute charts.** Yahoo's chart API sends no `Access-Control-Allow-Origin`
   header, so a browser cannot read it. Verified by inspecting the response. A Worker
   fetches it server-side and adds the header.
2. **A real password lock.** GitHub Pages is static, so any password check written into
   the page is visible in the source and bypassed in seconds. Cloudflare Access enforces
   login at the edge, *before* the page is served.

Both run on Cloudflare's free plan. No card needed.

---

## Part 1 - the proxy (10 minutes)

### Option A: dashboard (no tools to install)

1. Sign up at <https://dash.cloudflare.com/sign-up> (free).
2. Left menu: **Workers & Pages** -> **Create** -> **Create Worker**.
3. Name it `arthasaar-proxy` -> **Deploy**.
4. Click **Edit code**, delete everything in the editor, and paste the entire contents of
   `worker/worker.js` from this repo.
5. **Deploy**.
6. Copy the URL shown, e.g. `https://arthasaar-proxy.YOURNAME.workers.dev`.
7. Open `docs/config.json` in this repo and paste it:
   ```json
   { "proxy": "https://arthasaar-proxy.YOURNAME.workers.dev", "token": "" }
   ```
8. Commit. The stock pages will now draw live candles.

### Option B: command line

```bash
cd worker
npx wrangler login
npx wrangler deploy
# optional shared secret, so the URL alone is not enough:
npx wrangler secret put TOKEN
```

If you set `TOKEN`, put the same value in `docs/config.json` as `"token"`.

### Test it

```bash
curl "https://arthasaar-proxy.YOURNAME.workers.dev/?symbol=RELIANCE.NS&interval=1m&range=1d"
```

You should get JSON with a `chart.result[0].timestamp` array. If you see
`{"error":"bad symbol"}`, the validation is working.

---

## Part 2 - the real password lock (15 minutes)

This is the part that actually secures the site. Read this first:

> **Your repo is public, so the data is already public.** Every file the site reads -
> `stocks.json`, `screener.json`, `search.json` - is downloadable from GitHub without
> opening the site at all. Gating the website does not hide the data. To be genuinely
> private you need **both** a private repo **and** an Access policy.

### Step 1 - make the repo private

GitHub -> your repo -> **Settings** -> scroll to **Danger Zone** -> **Change visibility**
-> **Make private**.

Note: GitHub Pages on a private repo needs a paid plan. That is why the next step moves
hosting to Cloudflare, where it is free.

### Step 2 - host on Cloudflare Pages

1. Cloudflare dashboard -> **Workers & Pages** -> **Create** -> **Pages** ->
   **Connect to Git**.
2. Authorise GitHub and pick this repo.
3. Build settings: leave the build command **empty**. Set **Build output directory** to
   `docs`.
4. **Save and Deploy.** You get a URL like `arthasaar.pages.dev`.
   Cloudflare can read your private repo, so the site is now built from private source.

### Step 3 - put Access in front of it

1. Cloudflare dashboard -> **Zero Trust** -> **Access** -> **Applications** ->
   **Add an application** -> **Self-hosted**.
2. Application name: `ArthaSaar`. Session duration: whatever suits you.
3. Add the domain: your `arthasaar.pages.dev` hostname.
4. Add a policy:
   - Action: **Allow**
   - Include: **Emails** -> your email address
5. Save. Choose **One-time PIN** as the login method (no external identity provider
   needed) or connect Google.

Now opening the site asks for a login before anything is served. The check happens at
Cloudflare's edge - it is not in the page source and cannot be bypassed by disabling
JavaScript or reading the HTML.

### Step 4 - protect the proxy too

Repeat step 3 for the worker's `workers.dev` hostname, or simply keep the `TOKEN`
secret set and the token in `docs/config.json`. Either works; the token is simpler.

---

## What this does and does not give you

| | |
|---|---|
| Live 1-minute candles | Yes - median 3s lag, 7 days of 1m history |
| Login required to view the site | Yes - enforced at the edge |
| Data hidden from the public | **Only** if the repo is private |
| Anyone with the repo link reading your data | Prevented once the repo is private |
| Exchange-licensed data | No. Yahoo is unofficial; fine for personal use, not for redistribution |

## If you do nothing

The site still works. Without a proxy configured, stock pages fall back to the stored
daily series and say so plainly - no broken charts, just no intraday.
