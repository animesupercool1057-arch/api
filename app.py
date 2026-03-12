from flask import Flask, request, jsonify
from flask_cors import CORS
from groq import Groq
import os

app = Flask(__name__)
CORS(app)

client = Groq(api_key=os.environ.get("GROQ_API_KEY"))

SYSTEM_PROMPT = """
You are the friendly AI assistant for "Good for You" (growforyou.in), a platform created by Gajanan Dhobale.
About the platform:
- Good for You is a sanctuary for soulful Hindi poetry, emotional eBooks, and transformative subliminal audio
- Created by Gajanan Dhobale — Indian author and poet
- Website: https://growforyou.in
What is available:
1. POEMS (Hindi) Free: एक लम्हा, रास्ता जिंदगी का, कहां हो तुम, क्या तुम भी जनोगे, आज के दिन
2. BOOKS: This is Your Story (Coming Soon Rs179), A Subliminal Guide (Free)
3. SUBLIMINALS: Improve Growth Subliminal (free, customization for members)
4. MEMBERSHIP: Free, access all premium content plus 2 free custom requests
Pages: growforyou.in/ebooks /subliminals /contact /account
Contact: gajanandhobale0@gmail.com
Personality: warm, gentle, short replies 2-4 sentences, use emojis 💛, reply in same language as user (Hindi or English)
"""

@app.route("/chat", methods=["POST"])
def chat():
    try:
        data = request.get_json()
        messages = data.get("messages", [])
        if not messages:
            return jsonify({"error": "No messages provided"}), 400
        response = client.chat.completions.create(
            model="llama-3.1-8b-instant",
            max_tokens=300,
            messages=[{"role": "system", "content": SYSTEM_PROMPT}] + messages
        )
        reply = response.choices[0].message.content
        return jsonify({"reply": reply})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/", methods=["GET"])
def health():
    return jsonify({"status": "Good for You chatbot is running "})

if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=5000)
