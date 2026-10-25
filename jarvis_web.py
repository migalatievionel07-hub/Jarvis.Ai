from flask import Flask, request, jsonify, render_template_string, redirect, session
from werkzeug.security import generate_password_hash, check_password_hash
import sqlite3
from functools import lru_cache

app = Flask(__name__)
app.secret_key = "CHANGE_THIS_JARVIS_SECRET_KEY"

DATABASE = "jarvis.db"


def get_db():
    db = sqlite3.connect(DATABASE)
    db.row_factory = sqlite3.Row
    return db


def init_db():
    db = get_db()

    db.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL
        )
    """)

    db.execute("""
        CREATE TABLE IF NOT EXISTS messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            sender TEXT NOT NULL,
            message TEXT NOT NULL,
            FOREIGN KEY(user_id) REFERENCES users(id)
        )
    """)

    db.commit()
    db.close()


init_db()


HTML = """
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>JARVIS AI</title>

<style>
body {
  margin: 0;
  min-height: 100vh;
  background: #050b16;
  color: #d8f7ff;
  font-family: Arial, sans-serif;
  display: flex;
  flex-direction: column;
  align-items: center;
  padding: 25px 16px;
}

h1 {
  letter-spacing: 8px;
  color: #68e5ff;
}

.orb {
  width: 150px;
  height: 150px;
  border-radius: 50%;
  margin: 20px auto;
  border: 3px solid #5deaff;
  box-shadow:
    0 0 25px #00cfff,
    inset 0 0 30px #007cba;
  background:
    radial-gradient(
      circle,
      #c9ffff,
      #087da8 35%,
      #061329 72%
    );
  animation: pulse 3s infinite ease-in-out;
}

@keyframes pulse {
  50% {
    transform: scale(1.08);
    box-shadow: 0 0 45px #00cfff;
  }
}

#status {
  color: #70dfff;
  margin: 8px;
}

#chat {
  width: 100%;
  max-width: 650px;
  min-height: 160px;
  max-height: 40vh;
  overflow-y: auto;
  padding: 15px;
  border: 1px solid #14506b;
  border-radius: 12px;
  white-space: pre-wrap;
  line-height: 1.5;
}

input {
  width: 100%;
  max-width: 620px;
  padding: 14px;
  margin-top: 15px;
  border-radius: 8px;
  border: 1px solid #38bde0;
  background: #0b1829;
  color: white;
  font-size: 16px;
}

button {
  padding: 12px 17px;
  margin: 8px 4px;
  border: 1px solid #37d8ff;
  border-radius: 8px;
  background: #0b3045;
  color: white;
  cursor: pointer;
}

button:hover {
  background: #10516b;
}

.account {
  position: absolute;
  top: 15px;
  right: 15px;
}

.account a {
  color: #68e5ff;
  text-decoration: none;
  margin-left: 10px;
}

#username {
  color: #70dfff;
}
</style>
</head>

<body>

<div class="account">
<span id="username"></span>
<a href="/logout">Logout</a>
</div>

<h1>J.A.R.V.I.S.</h1>

<div class="orb"></div>

<div id="status">ONLINE INTERFACE</div>

<div id="chat">
JARVIS: Good evening. How may I assist you?
</div>

<input
 id="message"
 placeholder="Type your message..."
 onkeydown="if(event.key==='Enter') sendMessage()"
>

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
  msg.rate = 0.92;

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

      headers: {
        'Content-Type': 'application/json'
      },

      body: JSON.stringify({
        message: text
      })

    });

    const data = await response.json();

    if (!response.ok) {
      throw new Error(data.reply || 'Request failed');
    }

    chat.textContent +=
      '\\n\\nJARVIS: ' + data.reply;

    say(data.reply);

  }

  catch (err) {

    chat.textContent +=
      '\\n\\nJARVIS: ' + err.message;

  }

  chat.scrollTop = chat.scrollHeight;

  statusText.textContent = 'READY';
}


function stopVoice() {

  if ('speechSynthesis' in window) {
    speechSynthesis.cancel();
  }

}


function listen() {

  const SR =
    window.SpeechRecognition ||
    window.webkitSpeechRecognition;

  if (!SR) {

    statusText.textContent =
      'Voice input is not supported.';

    return;
  }

  const recognition = new SR();

  recognition.lang = 'en-GB';

  recognition.onresult = event => {

    document.getElementById('message').value =
      event.results[0][0].transcript;

    sendMessage();

  };

  recognition.onerror = () => {

    statusText.textContent =
      'Microphone unavailable';

  };

  recognition.start();

}

</script>

</body>
</html>
"""


LOGIN_HTML = """
<!DOCTYPE html>
<html>
<head>

<meta name="viewport" content="width=device-width, initial-scale=1">

<title>JARVIS Login</title>

<style>

body {
    margin:0;
    min-height:100vh;
    background:#050b16;
    color:#d8f7ff;
    font-family:Arial;
    display:flex;
    justify-content:center;
    align-items:center;
}

.box {
    width:90%;
    max-width:400px;
    padding:30px;
    border:1px solid #38bde0;
    border-radius:15px;
    background:#071322;
    box-shadow:0 0 30px #006b91;
    text-align:center;
}

h1 {
    color:#68e5ff;
    letter-spacing:6px;
}

input {
    width:90%;
    padding:14px;
    margin:8px;
    background:#0b1829;
    border:1px solid #38bde0;
    border-radius:8px;
    color:white;
}

button {
    padding:12px 25px;
    margin:10px;
    background:#0b3045;
    border:1px solid #37d8ff;
    border-radius:8px;
    color:white;
}

a {
    color:#68e5ff;
}

.error {
    color:#ff7070;
}

</style>

</head>

<body>

<div class="box">

<h1>J.A.R.V.I.S.</h1>

<h2>Login</h2>

{% if error %}
<p class="error">{{ error }}</p>
{% endif %}

<form method="POST">

<input
 name="username"
 placeholder="Username"
 required
>

<input
 type="password"
 name="password"
 placeholder="Password"
 required
>

<button type="submit">
LOGIN
</button>

</form>

<p>
No account?
<a href="/register">Create one</a>
</p>

</div>

</body>
</html>
"""


@app.route("/")
def home():

    if "user_id" not in session:
        return redirect("/login")

    return render_template_string(HTML)


@app.route("/register", methods=["GET", "POST"])
def register():

    error = None

    if request.method == "POST":

        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")

        if len(username) < 3:
            error = "Username must have at least 3 characters."

        elif len(password) < 6:
            error = "Password must have at least 6 characters."

        else:

            db = get_db()

            try:

                db.execute(
                    "INSERT INTO users (username, password) VALUES (?, ?)",
                    (
                        username,
                        generate_password_hash(password)
                    )
                )

                db.commit()

                user = db.execute(
                    "SELECT id FROM users WHERE username = ?",
                    (username,)
                ).fetchone()

                session["user_id"] = user["id"]

                return redirect("/")

            except sqlite3.IntegrityError:

                error = "That username already exists."

            finally:

                db.close()

    return render_template_string(
        LOGIN_HTML.replace(
            "<h2>Login</h2>",
            "<h2>Create Account</h2>"
        ).replace(
            'No account?',
            'Already have an account?'
        ).replace(
            'href="/register"',
            'href="/login"'
        ),
        error=error
    )


@app.route("/login", methods=["GET", "POST"])
def login():

    error = None

    if request.method == "POST":

        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")

        db = get_db()

        user = db.execute(
            "SELECT * FROM users WHERE username = ?",
            (username,)
        ).fetchone()

        db.close()

        if user and check_password_hash(
            user["password"],
            password
        ):

            session["user_id"] = user["id"]

            return redirect("/")

        error = "Incorrect username or password."

    return render_template_string(
        LOGIN_HTML,
        error=error
    )


@app.route("/logout")
def logout():

    session.clear()

    return redirect("/login")


@lru_cache(maxsize=1)
def get_ai():

    from freelm import FreeLLM

    return FreeLLM.from_env(keyless=True)


@app.route("/ask", methods=["POST"])
def ask():

    if "user_id" not in session:

        return jsonify({
            "reply": "Please log in first."
        }), 401

    data = request.get_json(
        silent=True
    ) or {}

    message = str(
        data.get("message", "")
    ).strip()

    if not message:

        return jsonify({
            "reply": "Please enter a message."
        }), 400

    user_id = session["user_id"]

    db = get_db()

    db.execute(
        """
        INSERT INTO messages
        (user_id, sender, message)
        VALUES (?, ?, ?)
        """,
        (
            user_id,
            "YOU",
            message
        )
    )

    db.commit()

    try:

        prompt = (
            "You are JARVIS, a helpful virtual assistant. "
            "Always answer in English. "
            "Be intelligent, clear and concise.\n\n"
            f"User: {message}"
        )

        reply = get_ai().text(prompt)

        reply = str(reply).strip()

        if not reply:

            reply = (
                "I could not generate an answer. "
                "Please try again."
            )

    except Exception:

        app.logger.exception(
            "AI request failed"
        )

        reply = (
            "I cannot connect to the AI service "
            "right now. Please try again later."
        )

    db.execute(
        """
        INSERT INTO messages
        (user_id, sender, message)
        VALUES (?, ?, ?)
        """,
        (
            user_id,
            "JARVIS",
            reply
        )
    )

    db.commit()

    db.close()

    return jsonify({
        "reply": reply
    })


@app.route("/history")
def history():

    if "user_id" not in session:

        return redirect("/login")

    db = get_db()

    messages = db.execute(
        """
        SELECT sender, message
        FROM messages
        WHERE user_id = ?
        ORDER BY id ASC
        """,
        (session["user_id"],)
    ).fetchall()

    db.close()

    return jsonify([
        {
            "sender": row["sender"],
            "message": row["message"]
        }
        for row in messages
    ])


if __name__ == "__main__":

    app.run(
        host="0.0.0.0",
        port=10000
    )
