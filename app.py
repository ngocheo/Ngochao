

#text/x-generic app.py ( Python script, UTF-8 Unicode text executable )
from flask import Flask, render_template_string, redirect, url_for, request, abort, flash
from flask_wtf import FlaskForm, CSRFProtect
from wtforms import SubmitField
import os, signal, subprocess, psutil
from dotenv import load_dotenv

# Tải biến môi trường từ file .env
load_dotenv()

app = Flask(__name__)
csrf = CSRFProtect(app)

# ================= CẤU HÌNH =================
app.config["SECRET_KEY"] = os.environ.get("FLASK_SECRET", "randomsecret")  # Flask session & CSRF
BOT_NAME = os.environ.get("BOT_NAME", "Shin Bot")
BOT_PATH = os.environ.get("BOT_PATH", "/sdcard/haobotvip/haobotvip/shin.py")  # Đường dẫn mặc định
PID_FILE = os.environ.get("PID_FILE", "/sdcard/haobotvip/haobotvip/shin.pid")
ADMIN_TOKEN = os.environ.get("ADMIN_TOKEN", "12345")  # Token bảo mật
LOG_FILE = os.environ.get("LOG_FILE", "/sdcard/haobotvip/haobotvip/shin.log")  # File log
# ============================================

# Form điều khiển
class ControlForm(FlaskForm):
    start = SubmitField("🚀 Start")
    stop = SubmitField("🛑 Stop")
    restart = SubmitField("♻️ Restart")
    refresh = SubmitField("🔄 Refresh")
    view_logs = SubmitField("📜 View Logs")

def is_running(pid):
    return psutil.pid_exists(pid)

def start():
    # Kiểm tra file bot
    if not os.path.isfile(BOT_PATH):
        return f"❌ Không tìm thấy file bot tại: {BOT_PATH}"

    # Kiểm tra bot đã chạy chưa
    if os.path.exists(PID_FILE):
        with open(PID_FILE, "r") as f:
            pid = int(f.read().strip())
        if is_running(pid):
            return f"⚠️ {BOT_NAME} đã chạy (PID={pid})"

    # Chạy bot với redirect stdout & stderr vào log
    try:
        with open(LOG_FILE, "a") as log_file:
            process = subprocess.Popen(
                ["python3", BOT_PATH],
                stdout=log_file,
                stderr=log_file,
                start_new_session=True
            )
        with open(PID_FILE, "w") as f:
            f.write(str(process.pid))
        return f"🚀 {BOT_NAME} đã khởi động (PID={process.pid})"
    except Exception as e:
        return f"❌ Lỗi khi khởi động bot: {e}"

def stop():
    if not os.path.exists(PID_FILE):
        return f"⚠️ {BOT_NAME} chưa chạy!"
    with open(PID_FILE, "r") as f:
        pid = int(f.read().strip())
    try:
        os.kill(pid, signal.SIGTERM)
    except ProcessLookupError:
        pass
    os.remove(PID_FILE)
    return f"🛑 {BOT_NAME} đã dừng!"

def status():
    if os.path.exists(PID_FILE):
        with open(PID_FILE, "r") as f:
            pid = int(f.read().strip())
        if is_running(pid):
            return f"✅ Đang chạy (PID={pid})"
        else:
            return "❌ Không tìm thấy tiến trình (PID chết)"
    return "❌ Chưa chạy"

@app.before_request
def check_auth():
    token = request.args.get("token") or request.form.get("token")
    if token != ADMIN_TOKEN:
        abort(403)

@app.route("/", methods=["GET", "POST"])
def home():
    form = ControlForm()
    message = None
    if form.validate_on_submit():
        if form.start.data:
            message = start()
        elif form.stop.data:
            message = stop()
        elif form.restart.data:
            stop_msg = stop()
            if "đã dừng" in stop_msg or "chưa chạy" in stop_msg:
                message = start()
            else:
                message = stop_msg
        elif form.view_logs.data:
            return redirect(url_for("view_logs", token=ADMIN_TOKEN))
        flash(message)

    return render_template_string("""
    <html>
    <head>
        <title>CMD Control - {{ bot_name }}</title>
        <style>
            body { background: #000; color: #0f0; font-family: monospace; }
            .cmd-box {
                border: 2px solid #0f0;
                padding: 20px;
                width: 700px;
                margin: 50px auto;
                background: #111;
            }
            .line { margin: 5px 0; }
            button { color: #0f0; background: none; border: none; cursor: pointer; font-family: monospace; font-size: 16px; }
            button:hover { text-decoration: underline; }
        </style>
    </head>
    <body>
        <div class="cmd-box">
            <div class="line">Microsoft Windows [Version 10.0.19045.4529]</div>
            <div class="line">(C) Bot Management Panel</div>
            <div class="line">&nbsp;</div>
            {% with messages = get_flashed_messages() %}
                {% if messages %}
                    <div class="line">{{ messages[-1] }}</div>
                {% endif %}
            {% endwith %}
            <div class="line">C:\\Bot\\{{ bot_name }}> status</div>
            <div class="line">{{ bot_status }}</div>
            <form method="post">
                {{ form.hidden_tag() }}
                <input type="hidden" name="token" value="{{ token }}">
                <div class="line">[1] {{ form.start() }} | [2] {{ form.stop() }} | [3] {{ form.restart() }}</div>
                <div class="line">[4] {{ form.view_logs() }}</div>
                <div class="line">[0] {{ form.refresh() }}</div>
            </form>
        </div>
    </body>
    </html>
    """, bot_name=BOT_NAME, bot_status=status(), form=form, token=ADMIN_TOKEN)

@app.route("/logs")
def view_logs():
    if not os.path.exists(LOG_FILE):
        logs = "⚠️ Chưa có file log."
    else:
        with open(LOG_FILE, "r", encoding="utf-8", errors="ignore") as f:
            lines = f.readlines()
            logs = "".join(lines[-100:])  # Lấy 100 dòng cuối
    return render_template_string("""
    <html>
    <head>
        <title>Logs - {{ bot_name }}</title>
        <meta http-equiv="refresh" content="3">
        <style>
            body { background: #000; color: #0f0; font-family: monospace; white-space: pre-wrap; }
            .log-box {
                border: 2px solid #0f0;
                padding: 10px;
                width: 90%;
                margin: 20px auto;
                background: #111;
                height: 600px;
                overflow-y: scroll;
            }
            a { color: #0f0; }
        </style>
    </head>
    <body>
        <div class="log-box">{{ logs }}</div>
        <div style="text-align:center; margin-top:10px;">
            <a href="{{ url_for('home', token=token) }}">⬅ Quay lại</a>
        </div>
    </body>
    </html>
    """, bot_name=BOT_NAME, logs=logs, token=ADMIN_TOKEN)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8082)