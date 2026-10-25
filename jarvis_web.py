            return redirect(url_for("home"))

        error = "Incorrect username or password."

    return render_template_string(
        AUTH_HTML, title="LOGIN", error=error, register=False
    )


@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))


@app.route("/ask", methods=["POST"])
def ask():
    if "user_id" not in session:
        return jsonify({"reply": "Please log in first."}), 401

    data = request.get_json(silent=True) or {}
    message = str(data.get("message", "")).strip()

    if not message:
        return jsonify({"reply": "Please enter a message."}), 400

    db = get_db()
    try:
        user_id = session["user_id"]

        db_execute(
            db,
            "INSERT INTO messages (user_id, role, message) VALUES (?, ?, ?)",
            (user_id, "YOU", message)
        )
        db.commit()

        history_rows = db_execute(
            db,
            """SELECT role, message FROM messages
               WHERE user_id = ? ORDER BY id ASC""",
            (user_id,)
        ).fetchall()

        reply = ask_ai(message, history_rows)

        db_execute(
            db,
            "INSERT INTO messages (user_id, role, message) VALUES (?, ?, ?)",
            (user_id, "JARVIS", reply)
        )
        db.commit()
    finally:
        db.close()

    return jsonify({"reply": reply})


@app.route("/history")
def history():
    if "user_id" not in session:
        return jsonify({"error": "Please log in."}), 401

    db = get_db()
    try:
        rows = db_execute(
            db,
            """SELECT role, message, created_at FROM messages
               WHERE user_id = ? ORDER BY id ASC""",
            (session["user_id"],)
        ).fetchall()
    finally:
        db.close()

    return jsonify([
        {
            "role": row["role"],
            "message": row["message"],
            "created_at": (
                str(row["created_at"]) if row["created_at"] else None
            )
        }
        for row in rows
    ])


@app.route("/upload", methods=["POST"])
def upload():
    if "user_id" not in session:
        return jsonify({"reply": "Please log in first."}), 401

    file = request.files.get("file")
    if not file or not file.filename:
        return jsonify({"reply": "Choose a file first."}), 400

    from werkzeug.utils import secure_filename
    filename = secure_filename(file.filename)
    if not filename:
        return jsonify({"reply": "Invalid filename."}), 400

    # This endpoint acknowledges the selected file but does not
    # save it permanently or analyse its contents yet.
    return jsonify({
        "reply": (
            f"File selected: {filename}. "
            "Content analysis is not configured yet."
        )
    })


@app.errorhandler(413)
def file_too_large(error):
    return jsonify({"reply": "File is too large. Maximum size is 10 MB."}), 413


if __name__ == "__main__":
    app.run(
        host="0.0.0.0",
        port=int(os.environ.get("PORT", "10000"))
    )
