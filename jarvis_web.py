import os
import sqlite3
from functools import lru_cache
from flask import (
    Flask, request, jsonify, render_template_string,
    redirect, session, url_for
)
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)

# Secret pentru sesiuni
app.secret_key = os.environ.get("SECRET_KEY", "jarvis-secret-change-this")

DB = "jarvis.db"


# =========================
# DATABASE
# =========================

def get_db():
    db = sqlite3.connect(DB)
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
            role TEXT NOT NULL,
            message TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    db.commit()
    db.close()


init_db()


# =========================
# AI
# =========================

@lru_cache(maxsize=1)
def get_ai():
    from freelm import FreeLLM
    return FreeLLM.from_env(keyless=True)


def ask_ai(message, history):
    try:
        conversation = ""

        for item in history[-10:]:
            conversation += (
                f"{item['role']}: {item['message']}\n"
            )

        prompt = f"""
You are JARVIS, a helpful and intelligent virtual assistant.

Rules:
- Answer clearly.
- You can answer in Romanian or English.
- Be friendly and concise.
- Remember the conversation context provided below.
- Do not claim that you control real devices.

Conversation:
{conversation}

User:
{message}

JARVIS:
"""

        reply = get_ai().text(prompt)

        if not reply:
            return "I could not generate an answer."

        return str(reply).strip()

    except Exception:
        app.logger.exception("AI request failed")
        return (
            "I cannot connect to the AI service right now. "
            "Please try again later."
        )


# =========================
# HTML
# =========================

HTML = """
<!DOCTYPE html>
<html lang="en">

<head>

<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1">

<title>J.A.R.V.I.S.</title>

<style>

* {
    box-sizing: border-box;
}

body {

    margin: 0;
    min-height: 100vh;

    background:
        radial-gradient(circle at center, #102c45 0%, #050b16 55%, #02050a 100%);

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

    text-shadow:
        0 0 10px #00cfff,
        0 0 25px #00cfff;
}

.top {

    width: 100%;
    max-width: 850px;

    display: flex;
    justify-content: space-between;
    align-items: center;

    margin-bottom: 10px;
}

.user {

    color: #70dfff;
}

.logout {

    color: white;
    text-decoration: none;

    border: 1px solid #37d8ff;

    padding: 8px 12px;

    border-radius: 8px;

    background: #0b3045;
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

        box-shadow:
            0 0 45px #00cfff,
            inset 0 0 40px #007cba;
    }
}

#status {

    color: #70dfff;

    margin: 8px;
}

#chat {

    width: 100%;
    max-width: 850px;

    min-height: 250px;
    max-height: 55vh;

    overflow-y: auto;

    padding: 18px;

    border: 1px solid #14506b;

    border-radius: 12px;

    background: rgba(5, 15, 28, 0.85);

    box-shadow:
        0 0 20px rgba(0, 207, 255, 0.15);

    white-space: pre-wrap;

    line-height: 1.5;
}

.input-area {

    width: 100%;
    max-width: 850px;

    display: flex;

    gap: 8px;

    margin-top: 15px;
}

input {

    flex: 1;

    padding: 14px;

    border-radius: 8px;

    border: 1px solid #38bde0;

    background: #0b1829;

    color: white;

    font-size: 16px;
}

button {

    padding: 12px 17px;

    border: 1px solid #37d8ff;

    border-radius: 8px;

    background: #0b3045;

    color: white;

    cursor: pointer;
}

button:hover {

    background: #10516b;
}

.buttons {

    margin-top: 10px;

    display: flex;

    gap: 8px;

    flex-wrap: wrap;

    justify-content: center;
}

.file {

    color: #70dfff;
}

</style>

</head>

<body>

<div class="top">

    <div class="user">
        👤 {{ username }}
    </div>

    <a class="logout" href="/logout">
        Logout
    </a>

</div>


<h1>J.A.R.V.I.S.</h1>

<div class="orb"></div>

<div id="status">
    ONLINE INTERFACE
</div>


<div id="chat">
JARVIS: Good evening. How may I assist you?
</div>


<div class="input-area">

    <input
        id="message"
        placeholder="Type your message..."
        onkeydown="if(event.key==='Enter') sendMessage()"
    >

    <button onclick="sendMessage()">
        Send
    </button>

</div>


<div class="buttons">

    <button onclick="listen()">
        🎤 Speak
    </button>

    <button onclick="stopVoice()">
        🔇 Stop voice
    </button>

    <label class="file">

        📎 File

        <input
            type="file"
            id="file"
            hidden
            onchange="uploadFile()"
        >

    </label>

</div>


<script>

const chat = document.getElementById("chat");

const statusText =
    document.getElementById("status");


function say(text) {

    if (!("speechSynthesis" in window))
        return;

    speechSynthesis.cancel();

    const msg =
        new SpeechSynthesisUtterance(text);

    msg.lang = "en-GB";

    msg.rate = 0.92;

    msg.pitch = 0.75;

    speechSynthesis.speak(msg);
}


async function sendMessage() {

    const input =
        document.getElementById("message");

    const text =
        input.value.trim();

    if (!text)
        return;

    input.value = "";

    chat.textContent +=
        "\\n\\nYOU: " + text;

    statusText.textContent =
        "THINKING...";

    try {

        const response =
            await fetch("/ask", {

                method: "POST",

                headers: {
                    "Content-Type":
                        "application/json"
                },

                body: JSON.stringify({
                    message: text
                })
            });


        const data =
            await response.json();


        if (!response.ok) {

            throw new Error(
                data.reply ||
                "Request failed"
            );
        }


        chat.textContent +=
            "\\n\\nJARVIS: " +
            data.reply;


        say(data.reply);


    } catch (error) {

        chat.textContent +=
            "\\n\\nJARVIS: " +
            error.message;
    }


    chat.scrollTop =
        chat.scrollHeight;

    statusText.textContent =
        "READY";
}


function stopVoice() {

    if ("speechSynthesis" in window)
        speechSynthesis.cancel();
}


function listen() {

    const SR =
        window.SpeechRecognition ||
        window.webkitSpeechRecognition;


    if (!SR) {

        statusText.textContent =
            "Voice input is not supported.";

        return;
    }


    const recognition =
        new SR();


    recognition.lang =
        "en-GB";


    recognition.onresult =
        event => {

            document
                .getElementById("message")
                .value =
                event.results[0][0].transcript;

            sendMessage();
        };


    recognition.onerror =
        () => {

            statusText.textContent =
                "Microphone unavailable";
        };


    recognition.start();
}


async function uploadFile() {

    const input =
        document.getElementById("file");

    const file =
        input.files[0];

    if (!file)
        return;


    const form =
        new FormData();

    form.append("file", file);


    statusText.textContent =
        "UPLOADING...";


    try {

        const response =
            await fetch("/upload", {

                method: "POST",

                body: form
            });


        const data =
            await response.json();


        chat.textContent +=
            "\\n\\nYOU: 📎 " +
            file.name;


        chat.textContent +=
            "\\nJARVIS: " +
            data.reply;


    } catch {

        chat.textContent +=
            "\\n\\nJARVIS: File upload failed.";
    }


    statusText.textContent =
        "READY";
}

</script>

</body>
</html>
"""


# =========================
# LOGIN PAGE
# =========================

LOGIN_HTML = """

<!DOCTYPE html>
<html>

<head>

<meta charset="UTF-8">

<meta name="viewport"
content="width=device-width, initial-scale=1">

<title>JARVIS Login</title>

<style>

body {

    margin: 0;

    min-height: 100vh;

    background:
        radial-gradient(
            circle,
            #102c45,
            #050b16 65%,
            #02050a
        );

    color: white;

    font-family: Arial;

    display: flex;

    align-items: center;

    justify-content: center;
}

.box {

    width: 90%;

    max-width: 400px;

    padding: 35px;

    background: rgba(5,15,28,.95);

    border: 1px solid #38d8ff;

    border-radius: 15px;

    box-shadow:
        0 0 30px rgba(0,200,255,.3);

}

h1 {

    text-align: center;

    color: #68e5ff;

    letter-spacing: 5px;
}

input {

    width: 100%;

    padding: 13px;

    margin-top: 12px;

    border-radius: 8px;

    border: 1px solid #38bde0;

    background: #0b1829;

    color: white;

    font-size: 16px;
}

.password {

    position: relative;
}

.password input {

    padding-right: 50px;
}

.eye {

    position: absolute;

    right: 10px;

    top: 23px;

    cursor: pointer;

    font-size: 20px;
}

button {

    width: 100%;

    padding: 13px;

    margin-top: 18px;

    border-radius: 8px;

    border: 1px solid #37d8ff;

    background: #0b3045;

    color: white;

    cursor: pointer;
}

a {

    color: #68e5ff;
}

.error {

    color: #ff7373;

    text-align: center;
}

</style>

</head>

<body>

<div class="box">

<h1>J.A.R.V.I.S.</h1>

{% if error %}

<div class="error">
{{ error }}
</div>

{% endif %}

<form method="POST">

<input
type="text"
name="username"
placeholder="Username"
required
>

<div class="password">

<input
id="password"
type="password"
name="password"
placeholder="Password"
required
>

<span
class="eye"
onclick="togglePassword()"
>
👁️
</span>

</div>

<button type="submit">
LOGIN
</button>

</form>

<p style="text-align:center">
No account?
<a href="/register">
Create one
</a>
</p>

</div>


<script>

function togglePassword() {

    const password =
        document.getElementById("password");

    const eye =
        document.querySelector(".eye");


    if (password.type === "password") {

        password.type = "text";

        eye.textContent = "🙈";

    } else {

        password.type = "password";

        eye.textContent = "👁️";
    }
}

</script>

</body>

</html>

"""


# =========================
# REGISTER
# =========================

REGISTER_HTML = """

<!DOCTYPE html>
<html>

<head>

<meta charset="UTF-8">

<meta name="viewport"
content="width=device-width, initial-scale=1">

<title>Create JARVIS Account</title>

<style>

body {

    margin:0;

    min-height:100vh;

    background:
        radial-gradient(
            circle,
            #102c45,
            #050b16 65%,
            #02050a
        );

    color:white;

    font-family:Arial;

    display:flex;

    justify-content:center;

    align-items:center;
}

.box {

    width:90%;

    max-width:400px;

    padding:35px;

    background:#050f1c;

    border:1px solid #38d8ff;

    border-radius:15px;

}

h1 {

    color:#68e5ff;

    text-align:center;

    letter-spacing:4px;
}

input {

    width:100%;

    padding:13px;

    margin-top:12px;

    border-radius:8px;

    border:1px solid #38bde0;

    background:#0b1829;

    color:white;

    font-size:16px;
}

button {

    width:100%;

    padding:13px;

    margin-top:18px;

    border-radius:8px;

    border:1px solid #37d8ff;

    background:#0b3045;

    color:white;
}

.error {

    color:#ff7373;

    text-align:center;
}

a {

    color:#68e5ff;
}

</style>

</head>

<body>

<div class="box">

<h1>CREATE ACCOUNT</h1>

{% if error %}

<div class="error">
{{ error }}
</div>

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

<input
type="password"
name="confirm"
placeholder="Confirm password"
required
>

<button type="submit">
CREATE ACCOUNT
</button>

</form>

<p style="text-align:center">

Already have an account?

<a href="/login">
Login
</a>

</p>

</div>

</body>

</html>

"""


# =========================
# ROUTES
# =========================

@app.route("/")
def home():

    if "user_id" not in session:
        return redirect(url_for("login"))

    return render_template_string(
        HTML,
        username=session["username"]
    )


@app.route("/login", methods=["GET", "POST"])
def login():

    error = None

    if request.method == "POST":

        username =
        request.form.get(
            "username", ""
        ).strip()

        password =
        request.form.get(
            "password", ""
        )


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

            session["user_id"] =
                user["id"]

            session["username"] =
                user["username"]

            return redirect(
                url_for("home")
            )


        error = "Wrong username or password."


    return render_template_string(
        LOGIN_HTML,
        error=error
    )


@app.route("/register", methods=["GET", "POST"])
def register():

    error = None

    if request.method == "POST":

        username =
            request.form.get(
                "username", ""
            ).strip()

        password =
            request.form.get(
                "password", ""
            )

        confirm =
            request.form.get(
                "confirm", ""
            )


        if len(username) < 3:

            error = "Username must have at least 3 characters."

        elif len(password) < 6:

            error = "Password must have at least 6 characters."

        elif password != confirm:

            error = "Passwords do not match."

        else:

            try:

                db = get_db()

                db.execute(
                    """
                    INSERT INTO users
                    (username, password)
                    VALUES (?, ?)
                    """,
                    (
                        username,
                        generate_password_hash(password)
                    )
                )

                db.commit()

                db.close()

                return redirect(
                    url_for("login")
                )

            except sqlite3.IntegrityError:

                error = "That username already exists."


    return render_template_string(
        REGISTER_HTML,
        error=error
    )


@app.route("/logout")
def logout():

    session.clear()

    return redirect(
        url_for("login")
    )


# =========================
# ASK JARVIS
# =========================

@app.route("/ask", methods=["POST"])
def ask():

    if "user_id" not in session:

        return jsonify({
            "reply": "Please login first."
        }), 401


    data =
        request.get_json(
            silent=True
        ) or {}


    message =
        str(
            data.get("message", "")
        ).strip()


    if not message:

        return jsonify({
            "reply":
                "Please enter a message."
        }), 400


    db = get_db()


    # Save user message

    db.execute(
        """
        INSERT INTO messages
        (user_id, role, message)
        VALUES (?, ?, ?)
        """,
        (
            session["user_id"],
            "YOU",
            message
        )
    )

    db.commit()


    history = db.execute(
        """
        SELECT role, message
        FROM messages
        WHERE user_id = ?
        ORDER BY id ASC
        """,
        (session["user_id"],)
    ).fetchall()


    reply = ask_ai(
        message,
        history
    )


    # Save JARVIS reply

    db.execute(
        """
        INSERT INTO messages
        (user_id, role, message)
        VALUES (?, ?, ?)
        """,
        (
            session["user_id"],
            "JARVIS",
            reply
        )
    )

    db.commit()

    db.close()


    return jsonify({
        "reply": reply
    })


# =========================
# UPLOAD FILE
# =========================

@app.route("/upload", methods=["POST"])
def upload():

    if "user_id" not in session:

        return jsonify({
            "reply": "Please login first."
        }), 401


    file = request.files.get("file")


    if not file:

        return jsonify({
            "reply": "No file selected."
        }), 400


    filename = file.filename


    # Momentan memorăm numele fișierului.
    # Analiza efectivă a imaginilor/documentelor
    # va fi adăugată în pasul următor.

    return jsonify({
        "reply":
            f"I received the file: {filename}"
    })


# =========================
# START
# =========================

if __name__ == "__main__":

    app.run(
        host="0.0.0.0",
        port=int(
            os.environ.get(
                "PORT",
                10000
            )
        )
    )
