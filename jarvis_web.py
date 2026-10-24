
import os
import requests
from flask import Flask, request, jsonify, render_template_string

app = Flask(__name__)

HTML = """
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>JARVIS AI</title>
<style>
* { box-sizing: border-box; }
body {
  margin: 0; min-height: 100vh; background: #050b16;
  color: #d8f7ff; font-family: Arial, sans-serif;
  display: flex; flex-direction: column; align-items: center;
  padding: 25px 16px;
}
h1 { letter-spacing: 8px; color: #68e5ff; }
.orb {
  width: 150px; height: 150px; border-radius: 50%;
  margin: 20px auto; border: 3px solid #5deaff;
  box-shadow: 0 0 25px #00cfff, inset 0 0 30px #007cba;
  background: radial-gradient(circle, #c9ffff, #087da8 35%, #061329 72%);
  animation: pulse 3s infinite ease-in-out;
}
@keyframes pulse {
  50% { transform: scale(1.08); box-shadow: 0 0 45px #00cfff; }
}
#status { color: #70dfff; margin: 8px; }
#chat {
  width: 100%; max-width: 650px; min-height: 160px;
  max-height: 40vh; overflow-y: auto; padding: 15px;
  border: 1px solid #14506b; border-radius: 12px;
  white-space: pre-wrap; line-height: 1.5;
}
input {
  width: 100%; max-width: 650px; padding: 14px;
  margin-top: 15px; border-radius: 8px;
  border: 1px solid #38bde0; background: #0b1829;
  color: white; font-size: 16px;
}
.buttons { display: flex; gap: 8px; margin-top: 10px; flex-wrap: wrap; }
button {
  padding: 12px 17px; border: 1px solid #37d8ff;
  border-radius: 8px; background: #0b3045;
  color: white; cursor: pointer;
}
button:hover { background: #10516b; }
</style>
</head>
<body>
<h1>J.A.R.V.I.S.</h1>
<div class="orb"></div>
<div id="status">ONLINE INTERFACE</div>
<div id="chat">JARVIS: Good evening. How may I assist you?</div>
<input id="message" placeholder="Speak or type your message..."
       onkeydown="if(event.key==='Enter') sendMessage()">
<div class="buttons">
  <button onclick="sendMessage()">Send</button>
  <button onclick="listen()">Speak</button>
  <button onclick="stopVoice()">Stop voice</button>
</div>
<script>
const chat = document.getElementById('chat');
const statusText = document.getElementById('status');

function say(text) {
  if (!('speechSynthesis' in window)) return;
  speechSynthesis.cancel();
  const msg = new SpeechSynthesisUtterance(text);
  msg.lang = 'en-GB';
  msg.rate = 0.92;
  msg.pitch = 0.75;
  const voices = speechSynthesis.getVoices();
  const voice = voices.find(v =>
    /^en(-GB)?/i.test(v.lang) &&
    /male|david|george|ryan|mark|daniel/i.test(v.name)
  );
  if (voice) msg.voice = voice;
  speechSynthesis.speak(msg);
}

async function sendMessage() {
  const input = document.getElementById('message');
  const text = input.value.trim();
  if (!text) return;
  input.value = '';
  chat.textContent += '\\n\\nYOU: ' + text;
  statusText.textContent = 'THINKING...';
  try {
    const response = await fetch('/ask', {
      method: 'POST',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({message: text})
    });
    const data = await response.json();
    if (!response.ok) throw new Error(data.error || 'Request failed');
    chat.textContent += '\\n\\nJARVIS: ' + data.reply;
    say(data.reply);
  } catch (err) {
    chat.textContent += '\\n\\nJARVIS: ' + err.message;
  }
  chat.scrollTop = chat.scrollHeight;
  statusText.textContent = 'READY';
}

function stopVoice() {
  if ('speechSynthesis' in window) speechSynthesis.cancel();
}

function listen() {
  const SpeechRecognition =
    window.SpeechRecognition || window.webkitSpeechRecognition;
  if (!SpeechRecognition) {
    statusText.textContent = 'Voice input is not supported in this browser.';
    return;
  }
  const recognition = new SpeechRecognition();
  recognition.lang = 'en-GB';
  recognition.onresult = event => {
    document.getElementById('message').value =
      event.results[0][0].transcript;
    sendMessage();
  };
  recognition.onerror = () => statusText.textContent = 'Microphone unavailable';
  recognition.start();
}
</script>
</body>
</html>
"""

@app.route("/")
def home():
    return render_template_string(HTML)

@app.route("/ask", methods=["POST"])
def ask():
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        return jsonify({
            "error": "JARVIS needs its online AI key configured."
        }), 503

    data = request.get_json(silent=True) or {}
    message = str(data.get("message", "")).strip()
    if not message:
        return jsonify({"error": "Please enter a message."}), 400

    url = (
        "https://generativelanguage.googleapis.com/"
        "v1beta/models/gemini-2.5-flash:generateContent"
    )
    payload = {
        "system_instruction": {
            "parts": [{
                "text": (
                    "You are JARVIS, a polite, intelligent AI assistant. "
                    "Always answer in English with a calm, sophisticated "
                    "and concise tone. Never claim to control devices."
                )
            }]
        },
        "contents": [{
            "parts": [{"text": message}]
        }]
    }

    try:
        result = requests.post(
            url,
            headers={
                "x-goog-api-key": api_key,
                "Content-Type": "application/json"
            },
            json=payload,
            timeout=45
        )
        if not result.ok:
            return jsonify({
                "error": "Online AI request failed. Check API setup and quota."
            }), 502

        result_data = result.json()
        reply = result_data["candidates"][0]["content"]["parts"][0]["text"]
        return jsonify({"reply": reply})

    except (requests.RequestException, KeyError, IndexError, ValueError):
        return jsonify({
            "error": "JARVIS could not reach the AI service. Try again."
        }), 502
