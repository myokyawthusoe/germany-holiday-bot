import datetime
import os
import sqlite3
from apscheduler.schedulers.background import BackgroundScheduler
from flask import Flask, jsonify, render_template, request
import requests

app = Flask(__name__)

TOKEN = "8936278623:AAHxIYiSUQBMKlTOb2fiG2VcV20q0DT50kw"
DB_NAME = "reminder_bot.db"


# --- Database ကို တည်ဆောက်ခြင်း (Tables ဖန်တီးခြင်း) ---
def init_db():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()

    # 1. Holiday Users Table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            chat_id TEXT PRIMARY KEY,
            state TEXT NOT NULL,
            status TEXT DEFAULT 'active'
        )
    """)

    # 2. Appointments Table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS appointments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            chat_id TEXT NOT NULL,
            date TEXT NOT NULL,
            time TEXT NOT NULL,
            text TEXT NOT NULL,
            status TEXT DEFAULT 'active'
        )
    """)

    # 3. Activity Logs / Transactions Table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS activity_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT NOT NULL,
            action_type TEXT NOT NULL,
            chat_id TEXT NOT NULL,
            details TEXT
        )
    """)

    conn.commit()
    conn.close()


init_db()


def log_activity(action_type, chat_id, details):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    cursor.execute(
        "INSERT INTO activity_logs (timestamp, action_type, chat_id, details) VALUES (?, ?, ?, ?)",
        (timestamp, action_type, chat_id, str(details)),
    )
    conn.commit()
    conn.close()


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/save", methods=["POST"])
def save():
    data = request.json
    chat_id = data.get("chatId")
    state = data.get("state")

    if not chat_id or not state:
        return jsonify({"success": False, "error": "Missing data"})

    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute(
        "INSERT OR REPLACE INTO users (chat_id, state, status) VALUES (?, ?, 'active')",
        (chat_id, state),
    )
    conn.commit()
    conn.close()

    log_activity("HOLIDAY_SAVE", chat_id, {"state": state})
    return jsonify({"success": True})


@app.route("/save_appointment", methods=["POST"])
def save_appointment():
    data = request.json
    chat_id = data.get("chatId")
    date = data.get("date")
    time = data.get("time")
    text = data.get("text")

    if not chat_id or not date or not time or not text:
        return jsonify({"success": False, "error": "Missing data"})

    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO appointments (chat_id, date, time, text, status) VALUES (?, ?, ?, ?, 'active')",
        (chat_id, date, time, text),
    )
    conn.commit()
    conn.close()

    log_activity(
        "APPOINTMENT_SAVE",
        chat_id,
        {"date": date, "time": time, "text": text},
    )
    return jsonify({"success": True})


@app.route("/unsubscribe", methods=["POST"])
def unsubscribe():
    data = request.json
    chat_id = data.get("chatId")

    if chat_id:
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        cursor.execute(
            "UPDATE users SET status = 'inactive' WHERE chat_id = ?", (chat_id,)
        )
        cursor.execute(
            "UPDATE appointments SET status = 'inactive' WHERE chat_id = ?",
            (chat_id,),
        )
        conn.commit()
        conn.close()

        log_activity("UNSUBSCRIBE", chat_id, {"status": "set to inactive"})
        return jsonify({"success": True})

    return jsonify({"success": False})


@app.route("/admin/view-db")
def view_db():
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    cursor.execute("SELECT * FROM users")
    users = [dict(row) for row in cursor.fetchall()]

    cursor.execute("SELECT * FROM appointments")
    appointments = [dict(row) for row in cursor.fetchall()]

    cursor.execute("SELECT * FROM activity_logs ORDER BY id DESC LIMIT 100")
    logs = [dict(row) for row in cursor.fetchall()]

    conn.close()

    def generate_table(rows):
        if not rows:
            return "<p style='color: #666; font-style: italic;'>No records found.</p>"
        html = "<table style='width:100%; border-collapse:collapse; background:white; margin-bottom:20px; box-shadow:0 2px 5px rgba(0,0,0,0.1);'>"
        html += "<tr style='background:#0066cc; color:white;'>"
        for key in rows[0].keys():
            html += f"<th style='padding:10px; border:1px solid #ddd; text-align:left;'>{key}</th>"
        html += "</tr>"
        for row in rows:
            html += "<tr>"
            for val in row.values():
                html += f"<td style='padding:10px; border:1px solid #ddd;'>{val}</td>"
            html += "</tr>"
        html += "</table>"
        return html

    html_content = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <title>Database Viewer</title>
        <style>
            body {{ font-family: sans-serif; padding: 20px; background: #f4f7f6; color: #333; max-width: 1000px; margin: auto; }}
            h2 {{ color: #1a1a1a; }}
            h3 {{ color: #0066cc; margin-top: 30px; border-bottom: 2px solid #0066cc; padding-bottom: 5px; }}
        </style>
    </head>
    <body>
        <h2>📊 Smart Reminder Hub - Database Inspector</h2>
        <hr>
        <h3>1. Users (Holidays)</h3>
        {generate_table(users)}
        
        <h3>2. Appointments (History & Active)</h3>
        {generate_table(appointments)}
        
        <h3>3. Recent Activity Logs (Transactions)</h3>
        {generate_table(logs)}
    </body>
    </html>
    """
    return html_content


def check_holidays_and_notify():
    pass  # စမ်းသပ်မှုအတွက် ခေတ္တပိတ်ထားပါသည်


# --- Appointment Reminder Check (Test Mode: Every 5 Minutes) ---
def check_appointments_and_notify():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()

    # မနက်ဖြန် ရက်စွဲကို တွက်ချက်မည် (သင်လိုချင်တဲ့ Logic အတိုင်း)
    tomorrow = datetime.date.today() + datetime.timedelta(days=1)
    tomorrow_str = tomorrow.strftime("%Y-%m-%d")

    print(
        f"--- [TEST] APPOINTMENT CHECKER RUNNING AT {datetime.datetime.now()} ---"
    )
    print(f"Looking for appointments on tomorrow: {tomorrow_str}")

    cursor.execute(
        "SELECT id, chat_id, time, text FROM appointments WHERE date = ? AND status = 'active'",
        (tomorrow_str,),
    )
    appts = cursor.fetchall()
    print(f"Found active appointments: {appts}")

    for appt_id, chat_id, time_val, text_val in appts:
        message = (
            f"⏰ *Appointment Reminder (မနက်ဖြန် ရှိပါသည်!)*\n"
            f"📅 *Date:* {tomorrow_str}\n"
            f"🕒 *Time:* {time_val}\n"
            f"📝 *Detail:* {text_val}\n\n"
            "🇲🇲 မနက်ဖြန်အတွက် Appointment ကို မမေ့နဲ့နော်။\n"
            "🇬🇧 Don't forget your appointment tomorrow."
        )
        telegram_url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
        res = requests.post(
            telegram_url,
            json={"chat_id": chat_id, "text": message, "parse_mode": "Markdown"},
        )
        print(f"Telegram API Response: {res.text}")

    # ပို့ပြီးသား appointment များကို status = 'completed' သို့ ပြောင်းမည်
    cursor.execute(
        "UPDATE appointments SET status = 'completed' WHERE date = ? AND status = 'active'",
        (tomorrow_str,),
    )
    conn.commit()
    conn.close()


# Scheduler Setup
scheduler = BackgroundScheduler()

# မနက် ၉ နာရီ ခေတ္တ comment ပိတ်ထားသည်
# scheduler.add_job(func=check_holidays_and_notify, trigger='cron', hour=16, minute=0)
# scheduler.add_job(func=check_appointments_and_notify, trigger='cron', hour=9, minute=0)

# 💡 စမ်းသပ်ရန်အတွက် ၅ မိနစ်တစ်ကြိမ် (interval) ဖြင့် ပြောင်းထားသည်
scheduler.add_job(
    func=check_appointments_and_notify, trigger="interval", minutes=5
)

scheduler.start()

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
