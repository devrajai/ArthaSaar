/* api/data.js — private repo se data serve karta hai (raw.githubusercontent / jsDelivr private repo par 404 dete hain).
   Usage: /api/data?p=data/global.json            (main branch)
          /api/data?ref=data&p=data/idx-NIFTY.json (data branch)
   Vercel env var GITHUB_TOKEN (fine-grained, read-only "Contents" on ArthaSaar) chahiye jab repo private ho.
   Edge par 5 min cache hota hai, isliye GitHub API calls kam rehti hain. */
const OWNER = "devrajai";
const REPO = "ArthaSaar";
const REFS = new Set(["main", "data"]);
const SAFE = /^data\/[A-Za-z0-9._\-\/]+\.(json|csv|txt)$/;
const TYPES = { json: "application/json; charset=utf-8", csv: "text/csv; charset=utf-8", txt: "text/plain; charset=utf-8" };

module.exports = async function handler(req, res) {
  /* repo public hai — data openly readable, cookie gate hata diya (private wapas ho to authOk restore karna) */
  const p = String((req.query && req.query.p) || "");
  const ref = REFS.has(String(req.query && req.query.ref)) ? String(req.query.ref) : "main";
  if (!SAFE.test(p) || p.indexOf("..") !== -1) {
    res.status(400).json({ error: "invalid path" });
    return;
  }
  const token = process.env.GITHUB_TOKEN || process.env.GH_TOKEN;
  const headers = { "User-Agent": "arthasaar-data-proxy" };
  if (token) {
    headers.Authorization = "Bearer " + token;
    headers.Accept = "application/vnd.github.raw";
  }
  try {
    /* Prefer the copy bundled in the Vercel deployment. This keeps private-repo data
       working even when GITHUB_TOKEN is not configured; GitHub remains the fallback. */
    const fs = require("fs"), path = require("path");
    const localPath = path.join(process.cwd(), p);
    if (ref === "main" && fs.existsSync(localPath)) {
      const body = await fs.promises.readFile(localPath);
      res.setHeader("Content-Type", TYPES[p.split(".").pop()] || TYPES.txt);
      res.setHeader("Cache-Control", "no-store");
      res.setHeader("X-Content-Type-Options", "nosniff");
      res.status(200).send(body);
      return;
    }
    const url = token
      ? "https://api.github.com/repos/" + OWNER + "/" + REPO + "/contents/" + p + "?ref=" + ref
      : "https://raw.githubusercontent.com/" + OWNER + "/" + REPO + "/" + ref + "/" + p;
    const r = await fetch(url, { headers });
    if (!r.ok) {
      res.setHeader("Cache-Control", "public, s-maxage=60");
      res.status(r.status === 404 ? 404 : 502).json({ error: "upstream " + r.status });
      return;
    }
    const body = Buffer.from(await r.arrayBuffer());
    res.setHeader("Content-Type", TYPES[p.split(".").pop()] || TYPES.txt);
    res.setHeader("Cache-Control", "public, max-age=60, s-maxage=300, stale-while-revalidate=900");
    res.setHeader("X-Content-Type-Options", "nosniff");
    res.status(200).send(body);
  } catch (e) {
    res.status(502).json({ error: "fetch failed" });
  }
};
