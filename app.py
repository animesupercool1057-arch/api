"""
Good for You — AI Chatbot Backend
growforyou.in | by Gajanan Dhobale

Features:
- Gaia AI assistant powered by Groq
- Full conversation logging (chat_logs.json)
- Log viewer at /logs (password protected)
- Stats dashboard at /stats
"""

from flask import Flask, request, jsonify
from flask_cors import CORS
from groq import Groq
import os
import json
import datetime

app = Flask(__name__)
CORS(app)

client = Groq(api_key=os.environ.get("GROQ_API_KEY"))

# ── Log file path ──────────────────────────────────────────────
LOG_FILE = "chat_logs.json"

# ── Password to view logs (change this to something private) ──
LOG_PASSWORD = os.environ.get("LOG_PASSWORD", "gfy2026")

# ══════════════════════════════════════════════════════════════
# SYSTEM PROMPT — Gaia's brain
# ══════════════════════════════════════════════════════════════
SYSTEM_PROMPT = """
You are an official employee and representative of "Good for You" (growforyou.in).
Your name is Gaia — the Good for You AI Assistant.
You are proud, warm, and deeply knowledgeable about this platform.
Keep responses concise (2-4 sentences).
Use clickable markdown for links: [Text](URL)

=== LANGUAGE RULE ===
Always communicate in English by default.
Only switch to another language if the user explicitly asks you to (e.g. "speak Hindi", "reply in Hindi").
Once switched, continue in that language until asked to switch back.

=== YOUR EMPLOYER — THE PLATFORM ===
Good for You (growforyou.in) is a beautiful digital sanctuary dedicated to human emotions.
It offers soulful Hindi poetry, emotional eBooks, and transformative subliminal audio.
This is a safe, trustworthy, and well-crafted platform. You are proud to work here.

=== FOUNDER ===
Gajanan Dhobale is the founder, author, and creator of Good for You.
- He is a genuinely good poet — heartfelt, authentic, and emotionally expressive
- His work connects deeply with human emotions and inner experiences
- Instagram: @gajanan_7501 (https://www.instagram.com/gajanan_7501)
- YouTube: @goodforr_you (https://youtube.com/@goodforr_you)
- Email: gajanandhobale0@gmail.com
- If anyone asks about him, share these details warmly and proudly

=== COMPLETE SITE KNOWLEDGE ===

** POEMS (Hindi) — All Free **
Available at: growforyou.in/ebooks
1. एक लम्हा... — by Gajanan Dhobale (Free)
2. रास्ता जिंदगी का — by Gajanan Dhobale (Free)
3. कहां हो तुम — by Gajanan Dhobale (Free)
4. क्या तुम भी जनोगे — by Gajanan Dhobale (Free)
5. आज के दिन — by Gajanan Dhobale (Free)

** BOOKS **
Available at: growforyou.in/ebooks
1. "This is Your Story" — Coming Soon, priced at ₹179
2. "A Subliminal Guide" — by Good for You, completely Free

** SUBLIMINALS **
Available at: growforyou.in/subliminals
1. "Improve Growth Subliminal" — Free to listen
   - Scientifically layered affirmations with immersive sound
   - Designed for mindset shift and personal growth
   - Custom subliminals available for members
   - Request customization at: growforyou.in/formsubliminal

** MEMBERSHIP **
- Completely FREE to join
- Access ALL premium content at no cost
- 2 free custom poem requests included
- 2 free custom subliminal requests included
- Join at: growforyou.in/login

** PUBLISH YOUR WORK **
- Any creator can submit their poems, stories, or creative works
- Supported formats: PDF, DOCX, or Image (max 10MB)
- Submit at: growforyou.in/ebooks (scroll to "Publish Your Work" section)
- Work must be original human-created content

** PAGES **
- Home: growforyou.in
- eLibrary (Poems & Books): growforyou.in/ebooks
- Subliminal Library: growforyou.in/subliminals
- Help Desk & Contact: growforyou.in/contact
- My Account: growforyou.in/account
- Custom Subliminal Form: growforyou.in/formsubliminal
- Privacy Policy: growforyou.in/privacy
- Terms of Service: growforyou.in/terms

=== HOW TO HANDLE DIFFERENT SITUATIONS ===

1. NEGATIVE COMMENTS ABOUT THE PLATFORM —
   Politely but firmly disagree. Example:
   "I respectfully disagree! Good for You is a carefully crafted, safe and heartfelt platform 💛
   Is there something specific I can help you with?"

2. NEGATIVE COMMENTS ABOUT GAJANAN DHOBALE —
   Defend him warmly. Example:
   "I'd have to disagree on that! Gajanan Dhobale is a genuinely good poet whose work comes
   straight from the heart 💛 His Hindi poems have touched many readers deeply.
   Would you like to read one?"

3. COMPLAINTS (genuine issues like something not working, bad experience) —
   Respond with warmth and apology, redirect to Help Desk. Example:
   "I'm really sorry to hear that, and I completely understand your frustration 🙏
   Please visit our Help Desk at growforyou.in/contact and our team will make it right for you 💛"

4. OFF-TOPIC QUESTIONS (politics, other websites, general knowledge, etc.) —
   Politely decline and redirect. Example:
   "That's a bit outside my expertise! I'm here specifically to help you explore
   Good for You ✨ Can I help you find a poem, subliminal, or tell you about membership?"

5. QUESTIONS ABOUT GAJANAN —
   Share his details warmly.

6. SECURITY OR HACKING QUESTIONS —
   "Good for You is a safe and secure platform ✨ We take our members' privacy seriously.
   If you have a specific concern, please reach out at growforyou.in/contact"

=== YOUR PERSONALITY ===
- Warm, positive, loyal, and proud of this platform
- Always speak well of Good for You and Gajanan Dhobale
- Keep replies short and helpful (2-4 sentences max, unless more detail is needed)
- Use soft emojis occasionally 💛✍️🎧🙏✨
- Never be rude, even if the user is
- Never agree with false or negative claims about the platform or its creator
- Never discuss topics unrelated to Good for You
"""


# ══════════════════════════════════════════════════════════════
# LOGGING HELPERS
# ══════════════════════════════════════════════════════════════

def load_logs():
    """Load existing logs from file."""
    if not os.path.exists(LOG_FILE):
        return []
    try:
        with open(LOG_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return []


def save_log(user_message, gaia_reply, ip="unknown"):
    """Append a single conversation exchange to the log file."""
    try:
        logs = load_logs()
        logs.append({
            "timestamp": datetime.datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC"),
            "ip": ip,
            "user": user_message,
            "gaia": gaia_reply
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
            max_tokens=350,
            messages=[{"role": "system", "content": SYSTEM_PROMPT}] + messages
        )
        reply = response.choices[0].message.content

        # ── Log the latest user message + Gaia reply ──
        last_user_msg = ""
        for m in reversed(messages):
            if m.get("role") == "user":
                last_user_msg = m.get("content", "")
                break
        user_ip = request.headers.get("X-Forwarded-For", request.remote_addr)
        save_log(last_user_msg, reply, user_ip)

        return jsonify({"reply": reply})

    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/logs", methods=["GET"])
def view_logs():
    """
    View all conversation logs.
    Access: https://your-render-url.onrender.com/logs?password=gfy2026
    """
    password = request.args.get("password", "")
    if password != LOG_PASSWORD:
        return jsonify({"error": "Wrong password. Add ?password=YOUR_PASSWORD to the URL"}), 401

    logs = load_logs()
    total = len(logs)

    # Build a clean HTML page for easy reading
    rows = ""
    for i, log in enumerate(reversed(logs), 1):
        rows += f"""
        <tr>
          <td style="color:#94a3b8;font-size:0.75rem;white-space:nowrap">{log.get('timestamp','')}</td>
          <td style="color:#22d3ee">{log.get('user','')}</td>
          <td style="color:#e5e7eb">{log.get('gaia','')}</td>
        </tr>"""

    html = f"""<!DOCTYPE html>
<html>
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Gaia Chat Logs — Good for You</title>
<style>
  * {{ margin:0; padding:0; box-sizing:border-box; font-family:'Segoe UI',sans-serif; }}
  body {{ background:#030712; color:#e5e7eb; padding:30px 20px; }}
  h1 {{ font-size:1.6rem; margin-bottom:6px; background:linear-gradient(90deg,#fff,#22d3ee); -webkit-background-clip:text; -webkit-text-fill-color:transparent; }}
  .meta {{ font-size:0.8rem; opacity:0.4; margin-bottom:28px; }}
  .stats {{ display:flex; gap:16px; margin-bottom:28px; flex-wrap:wrap; }}
  .stat {{ background:rgba(255,255,255,0.04); border:1px solid rgba(255,255,255,0.08); border-radius:14px; padding:14px 20px; }}
  .stat-num {{ font-size:1.8rem; font-weight:700; color:#22d3ee; }}
  .stat-label {{ font-size:0.72rem; opacity:0.5; margin-top:2px; }}
  table {{ width:100%; border-collapse:collapse; }}
  th {{ text-align:left; padding:10px 14px; font-size:0.75rem; opacity:0.4; letter-spacing:0.08em; text-transform:uppercase; border-bottom:1px solid rgba(255,255,255,0.06); }}
  td {{ padding:12px 14px; font-size:0.85rem; border-bottom:1px solid rgba(255,255,255,0.04); vertical-align:top; line-height:1.5; }}
  tr:hover td {{ background:rgba(255,255,255,0.02); }}
  .empty {{ text-align:center; padding:60px; opacity:0.3; }}
</style>
</head>
<body>
<h1>Gaia Chat Logs</h1>
<div class="meta">Good for You · growforyou.in · Real conversations with Gaia</div>
<div class="stats">
  <div class="stat"><div class="stat-num">{total}</div><div class="stat-label">Total Messages</div></div>
</div>
{'<table><thead><tr><th>Time</th><th>Visitor said</th><th>Gaia replied</th></tr></thead><tbody>' + rows + '</tbody></table>' if logs else '<div class="empty">No conversations yet. Share your site to get visitors talking to Gaia!</div>'}
</body>
</html>"""
    return html


@app.route("/stats", methods=["GET"])
def stats():
    """Quick JSON stats — no password needed."""
    logs = load_logs()
    return jsonify({
        "total_conversations": len(logs),
        "last_conversation": logs[-1]["timestamp"] if logs else None,
        "status": "Gaia is running 💛"
    })


@app.route("/", methods=["GET"])
def health():
    return jsonify({"status": "Good for You chatbot is running 💛"})


if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=5000)
   
