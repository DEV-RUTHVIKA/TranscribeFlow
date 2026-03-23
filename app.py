import os
import mysql.connector
from flask import Flask, render_template, request, redirect, url_for, send_file, session
from audio_to_text import transcribe_audio
from summarizer import generate_summary
from flask import jsonify
import json

app = Flask(__name__)

app.secret_key = os.urandom(24)

# MySQL Connection
conn = mysql.connector.connect(
    host="localhost",
    user="root",
    password="password",
    database="tflow",
    port=3307
)


UPLOAD_FOLDER = "uploads"
TRANSCRIPT_FOLDER = "transcripts"

ALLOWED_EXTENSIONS = {"mp3", "wav", "m4a"}

os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(TRANSCRIPT_FOLDER, exist_ok=True)

app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER


uploaded_filename = None
transcript_text_global = ""
summary_text_global = ""


def allowed_file(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS


@app.route("/")
def home():
    return redirect(url_for("login"))


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]

        cursor = conn.cursor()
        cursor.execute(
            "SELECT * FROM users WHERE username=%s AND password=%s",
            (username, password)
        )

        user = cursor.fetchone()

        if user:
            session['username'] = username
            return redirect(url_for("upload_audio"))
        else:
            return render_template("login.html", error="Invalid username or password")

    return render_template("login.html")


@app.route('/logout')
def logout():
    session.pop('username', None)
    return redirect(url_for('login'))


@app.route("/signup_page", methods=["GET", "POST"])
def signup():
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]
        confirm_password = request.form["confirm_password"]

        if password != confirm_password:
            return render_template("signup.html", error="Passwords do not match")

        cursor = conn.cursor()
        cursor.execute("SELECT * FROM users WHERE username=%s", (username,))
        existing_user = cursor.fetchone()

        if existing_user:
            return render_template("signup.html", error="User already exists")

        cursor.execute(
            "INSERT INTO users (username, password) VALUES (%s, %s)",
            (username, password)
        )
        conn.commit()

        return render_template(
            "login.html",
            success="Account created successfully! Please login."
        )

    return render_template("signup.html")


@app.route("/upload_audio")
def upload_audio():
    global uploaded_filename

    if 'username' not in session:
        return redirect(url_for('login'))

    recorded = request.args.get("recorded")

    if recorded:
        uploaded_filename = recorded

        return render_template(
            "upload.html",
            success=f"✅ {recorded} recorded successfully!",
            show_transcribe=True,
            audio_file=recorded
        )

    return render_template("upload.html")


@app.route("/upload", methods=["POST"])
def upload_file():
    global uploaded_filename

    if "file" not in request.files:
        return render_template("upload.html", error="Please choose a file to upload")

    file = request.files["file"]

    if file.filename == "":
        return render_template("upload.html", error="Please choose a file to upload")

    if not allowed_file(file.filename):
        return render_template("upload.html", error="Only MP3, WAV, M4A files are allowed")

    filepath = os.path.join(app.config["UPLOAD_FOLDER"], file.filename)
    file.save(filepath)

    uploaded_filename = file.filename

    return render_template(
        "upload.html",
        success=f" {file.filename} uploaded successfully!",
        show_transcribe=True
    )


@app.route("/transcribe", methods=["POST"])
def transcribe():
    global uploaded_filename, transcript_text_global

    audio_path = os.path.join(UPLOAD_FOLDER, uploaded_filename)

    transcript_text_global = transcribe_audio(audio_path)

    return render_template(
        "upload.html",
        success=f"{uploaded_filename} Transcribed Successfully!",
        show_transcribe=True,
        transcript=transcript_text_global,
        audio_file=uploaded_filename
    )


@app.route("/download/<filename>")
def download(filename):
    filepath = os.path.join(TRANSCRIPT_FOLDER, filename)
    return send_file(filepath, as_attachment=True)


@app.route("/download_json")
def download_json():

    global transcript_text_global, summary_text_global, uploaded_filename

    if not transcript_text_global or not summary_text_global:
        return "No data available to download."

    base = os.path.splitext(uploaded_filename)[0]
    json_filename = base + ".json"

    data = {
        "filename": uploaded_filename,
        "transcript": transcript_text_global,
        "summary": summary_text_global
    }

    json_path = os.path.join("transcripts", json_filename)

    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4)

    return send_file(json_path, as_attachment=True)


def get_next_voice_filename():
    files = os.listdir(UPLOAD_FOLDER)
    voice_files = [f for f in files if f.startswith(
        "voice") and f.endswith(".mp3")]
    return f"voice{len(voice_files)+1}.mp3"


@app.route("/record", methods=["POST"])
def record_audio():
    global uploaded_filename

    audio = request.files["audio"]

    filename = get_next_voice_filename()
    filepath = os.path.join(UPLOAD_FOLDER, filename)

    audio.save(filepath)

    uploaded_filename = filename

    return jsonify({
        "success": True,
        "filename": filename
    })


@app.route("/summarize", methods=["POST"])
def summarize():
    global transcript_text_global, summary_text_global, uploaded_filename

    summary_text_global = generate_summary(transcript_text_global)

    base = os.path.splitext(uploaded_filename)[0]
    txt_filename = base + ".txt"

    with open(os.path.join("transcripts", txt_filename), "w", encoding="utf-8") as f:
        f.write(
            f"Transcript:\n{transcript_text_global}\n\n"
            f"Summary:\n{summary_text_global}"
        )

    return render_template(
        "upload.html",
        show_transcribe=True,
        transcript=transcript_text_global,
        summary=summary_text_global,
        txt_file=txt_filename,
        audio_file=uploaded_filename
    )


@app.route('/uploads/<filename>')
def uploaded_file(filename):
    return send_file(os.path.join(UPLOAD_FOLDER, filename))


if __name__ == "__main__":
    app.run(debug=True)
