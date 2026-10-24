
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
  width: 100%; max-width: 620px; padding: 14px;
  margin-top: 15px; border-radius: 8px;
  border: 1px solid #38bde0; background: #0b1829;
  color: white; font-size: 16px;
}
button {
  padding: 12px 17px; margin: 8px 4px;
  border: 1px solid #37d8ff; border-radius: 8px;
  background: #0b3045; color: white; cursor: pointer;
}
</style>
</head>
<body>
<h1>J.A.R.V.I.S.</h1>
<div class="orb"></div>
<div id="status">ONLINE INTERFACE</div>
<div id="chat">JARVIS: Good evening. How may I assist you?</div>
<input id="message" placeholder="Type your message..."
 onkeydown="if(event.key==='Enter') sendMessage()">
<div>
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
  msg.pitch = 0.75;
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
    chat.textContent += '\\n\\nJARVIS: ' + data.reply;
    say(data.reply);
  } catch (err) {
    chat.textContent += '\\n\\nJARVIS: Please try again.';
  }
  chat.scrollTop = chat.scrollHeight;
  statusText.textContent = 'READY';
}

function stopVoice() {
  if ('speechSynthesis' in window) speechSynthesis.cancel();
}

function listen() {
  const SR = window.SpeechRecognition || window.webkitSpeechRecognition;
  if (!SR) {
    statusText.textContent = 'Voice input is not supported.';
    return;
  }
  const recognition = new SR();
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

from functools import lru_cache

@lru_cache(maxsize=1)
def get_ai():
    from freelm import FreeLLM
    return FreeLLM.from_env(keyless=True)

@app.route("/ask", methods=["POST"])
def ask():
    data = request.get_json(silent=True) or {}
    message = str(data.get("message", "")).strip()

    if not message:
        return jsonify({"reply": "Please enter a message."}), 400

    try:
        prompt = (
            "You are JARVIS, a helpful virtual assistant. "
            "Answer clearly and concisely. "
            "The user may write in Romanian or English.\n\n"
            f"User: {message}"
        )

        reply = get_ai().text(prompt)

        if not reply or not str(reply).strip():
            reply = "I could not get an answer. Please try again."
        else:
            reply = str(reply).strip()

        return jsonify({"reply": reply})

    except Exception as e:
        app.logger.exception("AI request failed")
        return jsonify({
            "reply": "I cannot connect to the AI service right now. Please try again later."
        }), 503
def ask():
    data = request.get_json(silent=True) or {}
    message = str(data.get("message", "")).strip()
    if not message:
        return jsonify({"reply": "Please enter a message."}), 400

    text = message.lower()

    if any(word in text for word in ["hello", "hi", "hey"]):
        reply = "Hello! I am JARVIS. How can I help you?"
    elif "your name" in text:
        reply = "My name is JARVIS, your virtual assistant."
    elif "time" in text:
        from datetime import datetime
        reply = "The server time is " + datetime.now().strftime("%H:%M") + "."
    elif "date" in text or "today" in text:
        from datetime import date
        reply = "Today's date is " + date.today().strftime("%B %d, %Y") + "."
    elif "help" in text:
        reply = "I can greet you, tell you the server time and date, and respond to a few simple commands."
    elif "thank" in text:
        reply = "You're welcome. Always happy to help."
    elif "how are you" in text:
        reply = "All systems are running. How may I assist you?"
    else:
        reply = "I am currently running in offline mode, so I cannot answer every question yet."

    return jsonify({"reply": reply})
