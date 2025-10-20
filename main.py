import telebot
import os
import requests
from bs4 import BeautifulSoup

BOT_TOKEN = os.getenv("BOT_TOKEN")
bot = telebot.TeleBot(BOT_TOKEN)

# 🔗 URL страницы с расписанием
URL = "https://nf.uust.ru/timetable/fulltime/files/(3)-20.10.25-25.10.25-PI.,-TMO.,-El.-ZO.html"

# 🕒 Расписание звонков
BELL_SCHEDULE = {
    "1": "08:00–09:35",
    "2": "09:45–11:20",
    "3": "12:00–13:35",
    "4": "13:45–15:20",
    "5": "15:40–17:15",
    "6": "17:25–19:00",
    "7": "19:10–20:45"
}


def process_location(text):
    if not text:
        return ""
    if "ЭИОС" in text:
        return "ЭИОС"
    return text.strip()


def get_schedule_for_group(target_group="ПИ-51з"):
    try:
        response = requests.get(URL, timeout=10)
        response.encoding = "windows-1251"
        response.raise_for_status()
    except requests.exceptions.RequestException:
        return "⚠️ Ошибка при загрузке расписания. Попробуй позже."

    soup = BeautifulSoup(response.text, "html.parser")

    days_data = {}
    current_day, current_date = "", ""

    for row in soup.find_all("tr"):
        # День недели
        day_cell = row.find("td", string=lambda t: t and any(
            d in str(t) for d in ["Пнд.", "Вт.", "Ср.", "Чт.", "Птн.", "Суб."]))
        if day_cell:
            current_day = day_cell.get_text(strip=True)

        # Дата
        date_cell = row.find("td", string=lambda t: t and "." in str(t) and "25" in str(t))
        if date_cell:
            current_date = date_cell.get_text(strip=True)

        # Ячейка группы
        pi_cell = row.find("td", id=f"{target_group}_", class_=f"{target_group}_")
        if pi_cell and current_day:
            text = pi_cell.get_text(" ", strip=True)
            if text and text != "1":
                para_cell = row.find("td", string=lambda t: t and "пара" in str(t))
                para_number = para_cell.get_text(strip=True) if para_cell else ""
                time_info = pi_cell.get("para", "")

                if current_day not in days_data:
                    days_data[current_day] = {"date": current_date, "lessons": []}

                parts = text.split(',')
                subject = parts[0].strip() if parts else ""
                type_teacher = parts[1].strip() if len(parts) > 1 else ""
                location_raw = ','.join(parts[2:]).strip() if len(parts) > 2 else ""
                location = process_location(location_raw)

                days_data[current_day]["lessons"].append({
                    "para": para_number,
                    "time": time_info,
                    "subject": subject,
                    "type_teacher": type_teacher,
                    "location": location
                })

    # Формируем красивый текст
    if not days_data:
        return f"❌ Расписание для {target_group} не найдено."

    result = [f"🎓 РАСПИСАНИЕ ДЛЯ {target_group}"]
    for day, data in days_data.items():
        result.append(f"\n📅 {day} ({data['date']})")
        result.append("-" * 50)
        for lesson in data["lessons"]:
            num = "".join(filter(str.isdigit, lesson["para"]))
            time = BELL_SCHEDULE.get(num, lesson["time"])
            type_short = lesson["type_teacher"].split('.')[0]
            result.append(f"🕒 {num} пара ({time}) | {lesson['subject']} | {type_short} | {lesson['location']}")
    return "\n".join(result)


# 🚀 Команды Telegram
@bot.message_handler(commands=['start'])
def start(message):
    bot.reply_to(message, "Привет! Я бот расписания 💡\nНапиши /raspisanie чтобы узнать расписание группы ПИ-51з.")


@bot.message_handler(commands=['raspisanie'])
def send_schedule(message):
    msg = bot.reply_to(message, "📡 Загружаю расписание, подожди...")
    schedule_text = get_schedule_for_group("ПИ-51з")
    bot.edit_message_text(schedule_text, chat_id=msg.chat.id, message_id=msg.message_id)


# 🔄 Запуск
print("✅ Бот запущен!")
bot.polling(none_stop=True)
