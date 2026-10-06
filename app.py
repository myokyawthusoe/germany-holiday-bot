import datetime
import json
from apscheduler.schedulers.background import BackgroundScheduler
from flask import Flask, jsonify, request
import requests

app = Flask(__name__)

# Telegram Bot အချက်အလက်များ (သင့် Bot Token ထည့်ရန်)
TOKEN = "YOUR_TELEGRAM_BOT_TOKEN"
DB_FILE = "users.json"


def load_users():
  try:
    with open(DB_FILE, "r") as f:
      return json.load(f)
  except:
    return []


def save_user(data):
  users = load_users()
  users = [u for u in users if u["chatId"] != data["chatId"]]
  users.append(data)
  with open(DB_FILE, "w") as f:
    json.dump(users, f)


@app.route("/")
def index():
  return app.send_static_file("index.html")


@app.route("/save", methods=["POST"])
def save():
  data = request.json
  save_user(data)
  return jsonify({"success": True})


def check_holidays_and_notify():
  users = load_users()
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
                f"⚠️ *မနက်ဖြန် ပိတ်ရက်နော်!* ({holiday_name})\n"
                "အကုန်ပိတ်မှာဖြစ်လို့ ဝယ်စရာရှိတာ ဝယ်ထားဦးနော်။"
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
      print(f"Error for user {chat_id}: {e}")


scheduler = BackgroundScheduler()
scheduler.add_job(
    func=check_holidays_and_notify, trigger="cron", hour=18, minute=0
)
scheduler.start()

if __name__ == "__main__":
  app.run(port=5000)
