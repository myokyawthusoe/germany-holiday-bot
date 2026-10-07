import datetime
import json
import os
from apscheduler.schedulers.background import BackgroundScheduler
from flask import Flask, jsonify, render_template, request
import requests

app = Flask(__name__)

TOKEN = "8936278623:AAHxIYiSUQBMKlTOb2fiG2VcV20q0DT50kw"
DB_FILE = "users.json"
APPT_FILE = "appointments.json"


def load_json(filename):
  try:
    with open(filename, "r") as f:
      return json.load(f)
  except:
    return []


def save_json(filename, data):
  with open(filename, "w") as f:
    json.dump(data, f)


def save_user(data):
  users = load_json(DB_FILE)
  users = [u for u in users if u["chatId"] != data["chatId"]]
  users.append(data)
  save_json(DB_FILE, users)


def save_appointment_db(data):
  appts = load_json(APPT_FILE)
  appts.append(data)
  save_json(APPT_FILE, appts)


def remove_all_user_data(chat_id):
  users = load_json(DB_FILE)
  users = [u for u in users if u["chatId"] != str(chat_id)]
  save_json(DB_FILE, users)

  appts = load_json(APPT_FILE)
  appts = [a for a in appts if a["chatId"] != str(chat_id)]
  save_json(APPT_FILE, appts)


@app.route("/")
def index():
  return render_template("index.html")


@app.route("/save", methods=["POST"])
def save():
  data = request.json
  save_user(data)
  return jsonify({"success": True})


@app.route("/save_appointment", methods=["POST"])
def save_appointment():
  data = request.json
  save_appointment_db(data)
  return jsonify({"success": True})


@app.route("/unsubscribe", methods=["POST"])
def unsubscribe():
  data = request.json
  chat_id = data.get("chatId")
  if chat_id:
    remove_all_user_data(chat_id)
    return jsonify({"success": True})
  return jsonify({"success": False})


# --- 1) နေ့စဉ် ညနေ ၄ နာရီ Holiday Check ---
def check_holidays_and_notify():
  users = load_json(DB_FILE)
  if not users:
    return

  tomorrow = datetime.date.today() + datetime.timedelta(days=1)
  year = tomorrow.year
  tomorrow_str = tomorrow.strftime("%Y-%m-%d")

  for user in users:
    chat_id = user["chatId"]
    state = user["state"]

    url = f"https://feiertage-api.de/api/?jahr={year}&land={state}"
    try:
      response = requests.get(url)
      if response.status_code == 200:
        holidays = response.json()
        for holiday_name, data in holidays.items():
          if data["datum"] == tomorrow_str:
            message = (
                f"⚠️ *မနက်ဖြန် ပိတ်ရက်ပါ! / Tomorrow is a public holiday!* —"
                f" *Holiday:* {holiday_name} — 🇲🇲 အကုန်ပိတ်မှာဖြစ်လို့ ဝယ်စရာရှိတာ"
                " ဝယ်ထားဦးနော်။ / 🇬🇧 Everything will be closed, so please"
                " buy what you need in advance."
            )
            telegram_url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
            requests.post(
                telegram_url,
                json={
                    "chat_id": chat_id,
                    "text": message,
                    "parse_mode": "Markdown",
                },
            )
            break
    except Exception as e:
      print(f"Holiday Error: {e}")


# --- 2) မနက် ၉ နာရီ Appointment Reminder (၁ ရက်ကြိုစစ်မည်) ---
def check_appointments_and_notify():
  appts = load_json(APPT_FILE)
  if not appts:
    return

  tomorrow = datetime.date.today() + datetime.timedelta(days=1)
  tomorrow_str = tomorrow.strftime("%Y-%m-%d")

  remaining_appts = []
  for appt in appts:
    if appt["date"] == tomorrow_str:
      chat_id = appt["chatId"]
      time_val = appt["time"]
      text_val = appt["text"]

      message = (
          f"⏰ *Appointment Reminder (မနက်ဖြန် Termin ရှိပါသည်!)*\n"
          f"📅 *Date:* {tomorrow_str}\n"
          f"🕒 *Time:* {time_val}\n"
          f"📝 *Detail:* {text_val}\n\n"
          "🇲🇲 မနက်ဖြန်အတွက် Appointment ကို မမေ့နဲ့နော်။\n"
          "🇬🇧 Don't forget your appointment tomorrow."
      )
      telegram_url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
      requests.post(
          telegram_url,
          json={"chat_id": chat_id, "text": message, "parse_mode": "Markdown"},
      )
    else:
      remaining_appts.append(appt)

  save_json(APPT_FILE, remaining_appts)


scheduler = BackgroundScheduler()
scheduler.add_job(
    func=check_holidays_and_notify, trigger="cron", hour=16, minute=0
)
scheduler.add_job(
    func=check_appointments_and_notify, trigger="cron", hour=9, minute=0
)
scheduler.start()

if __name__ == "__main__":
  port = int(os.environ.get("PORT", 5000))
  app.run(host="0.0.0.0", port=port)
