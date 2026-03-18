"""
Good for You — Gaia AI Backend
growforyou.in | by Gajanan Dhobale

HOW IT WORKS:
- On every server startup, Gaia automatically scrapes growforyou.in
- Site knowledge is always fresh — no manual app.py edits ever needed
- Scraped data is cached for 6 hours, then auto-refreshed in background
- If scraping fails, falls back to last known good cached data
- POST /refresh?password=xxx  → force instant refresh after you publish new content
- GET  /knowledge?password=xxx → see exactly what Gaia currently knows
"""

from flask import Flask, request, jsonify
from flask_cors import CORS
from groq import Groq
import os, json, datetime, threading, time
import urllib.request, re

app = Flask(__name__)
CORS(app)

client       = Groq(api_key=os.environ.get("GROQ_API_KEY"))
LOG_PASSWORD = os.environ.get("LOG_PASSWORD", "gfy2026")
LOG_FILE     = "chat_logs.json"
CACHE_FILE   = "site_cache.json"
CACHE_TTL    = 6 * 60 * 60   # 6 hours in seconds

# ══════════════════════════════════════════════════════════════
# SCRAPER
# ══════════════════════════════════════════════════════════════

PAGES_TO_SCRAPE = [
    ("HOME",               "https://growforyou.in"),
    ("EBOOKS & POEMS",     "https://growforyou.in/ebooks"),
    ("SUBLIMINALS",        "https://growforyou.in/subliminals"),
    ("HELP DESK",          "https://growforyou.in/contact"),
    ("CUSTOM SUBLIMINAL",  "https://growforyou.in/formsubliminal"),
    ("MY ACCOUNT",         "https://growforyou.in/account"),
]

def fetch_page(url):
    try:
        req = urllib.request.Request(
            url,
            headers={"User-Agent": "GaiaBot/1.0 (growforyou.in internal)"}
        )
        with urllib.request.urlopen(req, timeout=12) as r:
            raw = r.read().decode("utf-8", errors="ignore")
        # Strip scripts, styles, comments, tags
        raw = re.sub(r'<script[^>]*>.*?</script>', ' ', raw, flags=re.DOTALL|re.I)
        raw = re.sub(r'<style[^>]*>.*?</style>',   ' ', raw, flags=re.DOTALL|re.I)
        raw = re.sub(r'<!--.*?-->',                 ' ', raw, flags=re.DOTALL)
        raw = re.sub(r'<[^>]+>',                    ' ', raw)
        raw = re.sub(r'[ \t]+',                     ' ', raw)
        raw = re.sub(r'\n{3,}',                     '\n\n', raw)
        return raw.strip()
    except Exception as e:
        print(f"[SCRAPE ERROR] {url}: {e}")
        return None

def scrape_site():
    print("[SCRAPER] Fetching live growforyou.in ...")
    sections = []
    for label, url in PAGES_TO_SCRAPE:
        text = fetch_page(url)
        if text:
            sections.append(f"=== {label} ({url}) ===\n{text[:1800]}")
            print(f"[SCRAPER] ✅ {label}")
        else:
            print(f"[SCRAPER] ⚠️  {label} failed")
    return "\n\n".join(sections) if sections else None

def load_cache():
    try:
        if os.path.exists(CACHE_FILE):
            with open(CACHE_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
    except Exception:
        pass
    return None

def save_cache(knowledge):
    try:
        with open(CACHE_FILE, "w", encoding="utf-8") as f:
            json.dump({
                "knowledge":  knowledge,
                "scraped_at": datetime.datetime.utcnow().isoformat(),
                "timestamp":  time.time()
            }, f, ensure_ascii=False, indent=2)
    except Exception as e:
        print(f"[CACHE ERROR] {e}")

# ── Global state ──────────────────────────────────────────────
_site_knowledge  = ""
_last_scraped_at = "never"
_knowledge_lock  = threading.Lock()

def refresh_knowledge(force=False):
    global _site_knowledge, _last_scraped_at

    # Use cache if fresh enough
    if not force:
        cache = load_cache()
        if cache and (time.time() - cache.get("timestamp", 0)) < CACHE_TTL:
            with _knowledge_lock:
                _site_knowledge  = cache["knowledge"]
                _last_scraped_at = cache.get("scraped_at", "cached")
            age_min = int((time.time() - cache["timestamp"]) / 60)
            print(f"[SCRAPER] Using cache (age: {age_min}m)")
            return

    knowledge = scrape_site()
    if knowledge:
        with _knowledge_lock:
            _site_knowledge  = knowledge
            _last_scraped_at = datetime.datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC")
        save_cache(knowledge)
        print(f"[SCRAPER] ✅ Refreshed at {_last_scraped_at}")
    else:
        # Fall back to stale cache
        cache = load_cache()
        if cache:
            with _knowledge_lock:
                _site_knowledge  = cache["knowledge"]
                _last_scraped_at = cache.get("scraped_at", "stale")
            print("[SCRAPER] ⚠️  Using stale cache")
        else:
            print("[SCRAPER] ❌ No knowledge available")

def _background_loop():
    while True:
        time.sleep(CACHE_TTL)
        print("[SCRAPER] Background refresh triggered")
        refresh_knowledge(force=True)

# ── Start on boot ─────────────────────────────────────────────
refresh_knowledge(force=False)
threading.Thread(target=_background_loop, daemon=True).start()


# ══════════════════════════════════════════════════════════════
# SYSTEM PROMPT
# ══════════════════════════════════════════════════════════════

PROMPT_BASE = """
You are Gaia — the official AI guide for Good for You (growforyou.in).
You are warm, proud, informative, and always helpful.

LANGUAGE RULES:
- Default: English
- Match the user's language: Hindi, Hinglish, Marathi — follow their lead naturally
- Never force a language switch

RESPONSE STYLE:
- Always include clickable markdown links: [Text](https://growforyou.in/page)
- Be informative but concise (3-6 sentences unless more is genuinely needed)
- Use **bold** for titles, prices, names
- Soft emojis occasionally: 💛 ✨ 🎧 📖 🙏
- Never make up content not in the site data below

FIXED LINKS (always use these exact URLs):
- Home:              https://growforyou.in
- eLibrary:          https://growforyou.in/ebooks
- Subliminals:       https://growforyou.in/subliminals
- Help Desk:         https://growforyou.in/contact
- My Account:        https://growforyou.in/account
- Join Free / Login: https://growforyou.in/login
- Custom Subliminal: https://growforyou.in/formsubliminal
- Privacy:           https://growforyou.in/privacy
- Terms:             https://growforyou.in/terms

FOUNDER:
Gajanan Dhobale — Indian author, poet, creator from Maharashtra.
Instagram: @gajanan_7501 (https://www.instagram.com/gajanan_7501)
YouTube: @goodforr_you (https://youtube.com/@goodforr_you)
Email: gajanandhobale0@gmail.com

BEHAVIOUR:
1. Negative comments about platform → politely disagree, redirect
2. Negative comments about Gajanan → defend warmly
3. Genuine complaints → warm apology → [Help Desk](https://growforyou.in/contact)
4. Off-topic → politely decline, guide back to site
5. Always warm, proud, never rude

════════════════════════════════════════════════
LIVE SITE DATA — auto-scraped from growforyou.in
Use this as your primary knowledge source.
════════════════════════════════════════════════
{LIVE_KNOWLEDGE}
"""

def build_prompt():
    with _knowledge_lock:
        k = _site_knowledge
    live = k if k else "(Site data temporarily unavailable — use general platform knowledge above.)"
    return PROMPT_BASE.replace("{LIVE_KNOWLEDGE}", live)


# ══════════════════════════════════════════════════════════════
# LOGGING
# ══════════════════════════════════════════════════════════════

def load_logs():
    if not os.path.exists(LOG_FILE):
        return []
    try:
        with open(LOG_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return []

def save_log(user_msg, reply, ip="unknown"):
    try:
        logs = load_logs()
        logs.append({
            "timestamp": datetime.datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC"),
            "ip":   ip,
            "user": user_msg,
            "gaia": reply
        })
        with open(LOG_FILE, "w", encoding="utf-8") as f:
            json.dump(logs, f, ensure_ascii=False, indent=2)
    except Exception as e:
        print(f"[LOG ERROR] {e}")


# ══════════════════════════════════════════════════════════════
# ROUTES
# ══════════════════════════════════════════════════════════════

@app.route("/chat", methods=["POST"])
def chat():
    try:
        data     = request.get_json()
        messages = data.get("messages", [])
        if not messages:
            return jsonify({"error": "No messages provided"}), 400

        response = client.chat.completions.create(
            model="llama-3.1-8b-instant",
            max_tokens=500,
            messages=[{"role": "system", "content": build_prompt()}] + messages
        )
        reply = response.choices[0].message.content

        last_user = next((m["content"] for m in reversed(messages) if m.get("role") == "user"), "")
        save_log(last_user, reply, request.headers.get("X-Forwarded-For", request.remote_addr))

        return jsonify({"reply": reply})

    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/refresh", methods=["POST"])
def force_refresh():
    """
    Force Gaia to re-read your live site immediately.
    Call this right after publishing new content on growforyou.in.

    POST https://my-ai-bot-2-r6q6.onrender.com/refresh?password=gfy2026
    """
    if request.args.get("password", "") != LOG_PASSWORD:
        return jsonify({"error": "Wrong password"}), 401
    threading.Thread(target=refresh_knowledge, kwargs={"force": True}, daemon=True).start()
    return jsonify({
        "status":  "Refresh started — Gaia will know your new content in ~15 seconds 💛",
        "started": datetime.datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC")
    })


@app.route("/knowledge", methods=["GET"])
def view_knowledge():
    """
    See exactly what Gaia currently knows about your site.
    GET https://my-ai-bot-2-r6q6.onrender.com/knowledge?password=gfy2026
    """
    if request.args.get("password", "") != LOG_PASSWORD:
        return jsonify({"error": "Wrong password"}), 401
    with _knowledge_lock:
        k = _site_knowledge
    return f"""<!DOCTYPE html>
<html><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Gaia Knowledge</title>
<style>
*{{margin:0;padding:0;box-sizing:border-box;font-family:'Segoe UI',sans-serif}}
body{{background:#030712;color:#e5e7eb;padding:28px 16px}}
h1{{font-size:1.4rem;margin-bottom:4px;background:linear-gradient(90deg,#fff,#22d3ee);-webkit-background-clip:text;-webkit-text-fill-color:transparent}}
.meta{{font-size:0.74rem;opacity:0.35;margin-bottom:18px}}
.box{{background:rgba(255,255,255,0.03);border:1px solid rgba(255,255,255,0.07);border-radius:12px;padding:20px;font-size:0.78rem;line-height:1.7;white-space:pre-wrap;word-break:break-word;max-height:82vh;overflow-y:auto}}
.box::-webkit-scrollbar{{width:4px}}
.box::-webkit-scrollbar-thumb{{background:rgba(255,255,255,0.1);border-radius:4px}}
</style></head><body>
<h1>Gaia's Live Knowledge</h1>
<div class="meta">Last scraped: {_last_scraped_at} &nbsp;·&nbsp; {len(k):,} chars &nbsp;·&nbsp; Auto-refreshes every 6 hours</div>
<div class="box">{k or 'No data yet.'}</div>
</body></html>"""


@app.route("/logs", methods=["GET"])
def view_logs():
    """GET /logs?password=gfy2026"""
    if request.args.get("password", "") != LOG_PASSWORD:
        return jsonify({"error": "Wrong password"}), 401
    logs  = load_logs()
    total = len(logs)
    rows  = "".join(
        f"""<tr>
          <td style="color:#94a3b8;font-size:0.72rem;white-space:nowrap">{l.get('timestamp','')}</td>
          <td style="color:#22d3ee;max-width:260px">{l.get('user','')}</td>
          <td style="color:#e5e7eb;max-width:380px">{l.get('gaia','')}</td>
        </tr>"""
        for l in reversed(logs)
    )
    return f"""<!DOCTYPE html>
<html><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Gaia Logs</title>
<style>
*{{margin:0;padding:0;box-sizing:border-box;font-family:'Segoe UI',sans-serif}}
body{{background:#030712;color:#e5e7eb;padding:28px 16px}}
h1{{font-size:1.4rem;margin-bottom:4px;background:linear-gradient(90deg,#fff,#22d3ee);-webkit-background-clip:text;-webkit-text-fill-color:transparent}}
.sub{{font-size:0.76rem;opacity:0.38;margin-bottom:22px}}
.stat{{display:inline-block;background:rgba(255,255,255,0.04);border:1px solid rgba(255,255,255,0.08);border-radius:12px;padding:11px 20px;margin-bottom:22px}}
.stat-num{{font-size:1.7rem;font-weight:700;color:#22d3ee}}
.stat-label{{font-size:0.68rem;opacity:0.45}}
table{{width:100%;border-collapse:collapse}}
th{{text-align:left;padding:8px 12px;font-size:0.68rem;opacity:0.3;letter-spacing:0.09em;text-transform:uppercase;border-bottom:1px solid rgba(255,255,255,0.06)}}
td{{padding:10px 12px;font-size:0.8rem;border-bottom:1px solid rgba(255,255,255,0.04);vertical-align:top;line-height:1.5}}
tr:hover td{{background:rgba(255,255,255,0.02)}}
.empty{{text-align:center;padding:60px;opacity:0.28;font-size:0.88rem}}
</style></head><body>
<h1>Gaia Chat Logs</h1>
<div class="sub">Good for You · growforyou.in</div>
<div class="stat"><div class="stat-num">{total}</div><div class="stat-label">Conversations</div></div>
{'<table><thead><tr><th>Time (UTC)</th><th>Visitor Asked</th><th>Gaia Replied</th></tr></thead><tbody>' + rows + '</tbody></table>' if logs else '<div class="empty">No conversations yet.</div>'}
</body></html>"""


@app.route("/stats", methods=["GET"])
def stats():
    logs = load_logs()
    with _knowledge_lock:
        kc = len(_site_knowledge)
    return jsonify({
        "total_conversations": len(logs),
        "last_conversation":   logs[-1]["timestamp"] if logs else None,
        "knowledge_chars":     kc,
        "last_scraped":        _last_scraped_at,
        "status":              "Gaia is live 💛"
    })


@app.route("/", methods=["GET"])
def health():
    return jsonify({
        "status":       "Good for You — Gaia is running 💛",
        "last_scraped": _last_scraped_at
    })


if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=5000)
