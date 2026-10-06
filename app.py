def check_holidays_and_notify():
  users = load_users()
  for user in users:
    chat_id = user["chatId"]
    state = user["state"]

    # Test လုပ်ရန်အတွက် ပိတ်ရက် ရှိသည်ဖြစ်စေ၊ မရှိသည်ဖြစ်စေ ချက်ချင်း ပို့မည်
    message = (
        f"⚠️ *Test Message:* သင့်ရဲ့ ပြည်နယ် ({state}) အတွက် Test လုပ်နေခြင်းဖြစ်ပါသည်။"
        " — *Holiday:* Test Holiday — 🇲🇲 အကုန်ပိတ်မှာဖြစ်လို့ ဝယ်စရာရှိတာ"
        " ဝယ်ထားဦးနော်။ / 🇬🇧 Everything will be closed, so please"
        " buy what you need in advance."
    )
    telegram_url = f"https://api.telegram.org/bot8936278623:AAHxIYiSUQBMKlTOb2fiG2VcV20q0DT50kw/sendMessage"
    response = requests.post(
        telegram_url,
        json={"chat_id": chat_id, "text": message, "parse_mode": "Markdown"},
    )
    print("Telegram Response:", response.text)
