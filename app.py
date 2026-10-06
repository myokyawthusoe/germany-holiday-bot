import datetime
import json
import os
from apscheduler.schedulers.background import BackgroundScheduler
from flask import Flask, jsonify, render_template, request
import requests

app = Flask(__name__)

# Telegram Token
TOKEN = "8936278623:AAHxIYiSUQBMKlTOb2fiG2VcV20q0DT50kw"
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


def remove_user(chat_id):
  users = load_users()
  users = [u for u in users if u["chatId"] != str(chat_id)]
  with open(DB_FILE, "w") as f:
    json.dump(users, f)


@app.route("/")
def index():
  return render_template("index.html")


@app.route("/save", methods=["POST"])
def save():
  data = request.json
  save_user(data)
  # Test လုပ်ရန် Save ပြီးတာနဲ့ ချက်ချင်း Telegram ဆီ စာပို့မည်
  send_test_message(data["chatId"], data["state"])
  return jsonify({"success": True})


@app.route("/unsubscribe", methods=["POST"])
def unsubscribe():
  data = request.json
  chat_id = data.get("chatId")
  if chat_id:
    remove_user(chat_id)
    return jsonify({"success": True})
  return jsonify({"success": False})


def send_test_message(chat_id, state):
  message = (
                f"⚠️ *မနက်ဖြန် ပိတ်ရက်ပါ! / Tomorrow is a public holiday!*\n"
                f"🎉 *Holiday:* {holiday_name}\n\n"
                "🇲🇲 အကုန်ပိတ်မှာဖြစ်လို့ ဝယ်စရာရှိတာ ဝယ်ထားဦးနော်။\n"
                "🇬🇧 Everything will be closed, so please buy what you need"
                " in advance."
            )
  telegram_url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
  response = requests.post(
      telegram_url, json={"chat_id": chat_id, "text": message, "parse_mode": "Markdown"}
  )
  print("Telegram API Response:", response.text)


if __name__ == "__main__":
  app.run(host="0.0.0.0", port=5000, debug=True)
