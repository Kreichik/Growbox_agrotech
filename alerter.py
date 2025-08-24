#!/usr/bin/env python3
import os
import csv
import time
import datetime
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from collections import deque
import sqlite3
import requests
from dotenv import load_dotenv


# STATE_FILE_TO_RESET = "last_alert_time.txt"
# if os.path.exists(STATE_FILE_TO_RESET):
#     try:
#         os.remove(STATE_FILE_TO_RESET)
#         print(f"Файл состояния '{STATE_FILE_TO_RESET}' удален. Кулдаун сброшен.")
#     except OSError as e:
#         print(f"Ошибка при удалении файла состояния: {e}")

load_dotenv()

SENDER_EMAIL = os.getenv("ALERTER_EMAIL")
SENDER_PASSWORD = os.getenv("ALERTER_PASSWORD")
TEMP_MIN = 23.0
TEMP_MAX = 30.0
HUMIDITY_MIN = 40.0
HUMIDITY_MAX = 60.0
CHECK_INTERVAL_SECONDS = 10
DATA_MAX_AGE_MINUTES = 15
ALERT_COOLDOWN_SECONDS = 60 * 120
BOT_TOKEN = os.getenv("BOT_TOKEN")
LAST_ALERT_STATE_FILE = "last_alert_time.txt"
CHECK_LOCK_FILE = "alert_check.lock"

DB_FILE = "telegram_users.db"


def send_alert_email(subject, body):
    if not SENDER_PASSWORD:
        print("ОШИБКА: Пароль для email не установлен.")
        return

    try:
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        cursor.execute("SELECT email FROM users WHERE email IS NOT NULL AND email != ''")
        recipients = [row[0] for row in cursor.fetchall()]
        conn.close()
    except Exception as e:
        print(f"Критическая ошибка при чтении email'ов из БД: {e}")
        return

    if not recipients:
        print("Нет подписчиков на Email-рассылку.")
        return

    try:
        msg = MIMEMultipart()
        msg['From'] = SENDER_EMAIL
        msg['Subject'] = subject
        msg.attach(MIMEText(body, 'plain', 'utf-8'))

        server = smtplib.SMTP_SSL('smtp.mail.ru', 465)
        server.login(SENDER_EMAIL, SENDER_PASSWORD)
        server.sendmail(SENDER_EMAIL, recipients, msg.as_string())
        server.quit()
        print(f"Email успешно отправлен {len(recipients)} подписчикам.")
    except Exception as e:
        print(f"Ошибка при отправке email: {e}")


def send_telegram_alert(body: str):
    print("Начинаю рассылку в Telegram...")
    try:
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        cursor.execute("SELECT user_id FROM users WHERE notifications_enabled = 1")
        user_ids = [row[0] for row in cursor.fetchall()]
        conn.close()

        if not user_ids:
            print("Нет активных подписчиков в Telegram.")
            return

        url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
        for user_id in user_ids:
            payload = {'chat_id': user_id, 'text': body}
            try:
                requests.post(url, json=payload, timeout=5)
            except requests.RequestException:
                pass
    except Exception as e:
        print(f"Ошибка в send_telegram_alert: {e}")


def check_and_alert():
    print("\n--- [DEBUG] Начало новой проверки ---")

    try:
        lock_fd = os.open(CHECK_LOCK_FILE, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
    except FileExistsError:
        print("[DEBUG] Lock-файл уже существует, другая проверка активна. Пропускаю.")
        return

    try:
        now = datetime.datetime.now()

        print("[DEBUG] 1. Проверяю кулдаун...")
        if os.path.isfile(LAST_ALERT_STATE_FILE):
            with open(LAST_ALERT_STATE_FILE, 'r') as f:
                try:
                    last_alert_timestamp = float(f.read().strip())
                    seconds_since_last_alert = (
                                now - datetime.datetime.fromtimestamp(last_alert_timestamp)).total_seconds()
                    if seconds_since_last_alert < ALERT_COOLDOWN_SECONDS:
                        print(
                            f"[DEBUG] Кулдаун активен. Осталось {int(ALERT_COOLDOWN_SECONDS - seconds_since_last_alert)} сек. Выход.")
                        return
                except (ValueError, TypeError):
                    pass
        print("[DEBUG] Кулдаун неактивен.")

        print("[DEBUG] 2. Ищу файл данных...")
        current_date = now.strftime("%Y-%m-%d")
        csv_filename = f'box_data/{current_date}.csv'
        if not os.path.isfile(csv_filename):
            print(f"[DEBUG] Файл данных {csv_filename} не найден. Выход.")
            return
        print(f"[DEBUG] Файл данных найден: {csv_filename}")

        print("[DEBUG] 3. Читаю последнюю строку из файла...")
        with open(csv_filename, 'r', newline='') as f:
            last_row_iter = deque(csv.DictReader(f), maxlen=1)
        if not last_row_iter:
            print("[DEBUG] Файл данных пуст. Выход.")
            return
        last_row = last_row_iter[0]
        print(f"[DEBUG] Последняя строка: {last_row}")

        print("[DEBUG] 4. Проверяю возраст данных...")
        timestamp_str = last_row.get("timestamp", "")
        if not timestamp_str:
            print("[DEBUG] Временная метка отсутствует. Выход.")
            return
        try:
            timestamp_dt = datetime.datetime.fromisoformat(timestamp_str)
            data_age_seconds = (now - timestamp_dt).total_seconds()
            if data_age_seconds > DATA_MAX_AGE_MINUTES * 60:
                print(f"[DEBUG] Данные слишком старые ({int(data_age_seconds)} сек). Выход.")
                return
        except ValueError:
            print(f"[DEBUG] Неверный формат временной метки: '{timestamp_str}'. Выход.")
            return
        print(f"[DEBUG] Возраст данных в норме ({int(data_age_seconds)} сек).")

        print("[DEBUG] 5. Анализирую показатели...")
        problem_messages = []

        air_temp_str = last_row.get("air_temperature", "").strip()
        if air_temp_str:
            try:
                air_temp = float(air_temp_str)
                print(f"[DEBUG]   Температура: {air_temp}°C")
                if air_temp < TEMP_MIN or air_temp > TEMP_MAX:
                    problem_messages.append(f"❗️ Температура: {air_temp}°C (норма: {TEMP_MIN}-{TEMP_MAX}°C)")
            except ValueError:
                print(f"[DEBUG]   Ошибка конвертации температуры: '{air_temp_str}' не является числом.")
        else:
            print("[DEBUG]   Поле 'air_temperature' пустое.")

        air_humidity_str = last_row.get("air_humidity", "").strip()
        if air_humidity_str:
            try:
                air_humidity = float(air_humidity_str)
                print(f"[DEBUG]   Влажность: {air_humidity}%")
                if air_humidity < HUMIDITY_MIN or air_humidity > HUMIDITY_MAX:
                    problem_messages.append(f"❗️ Влажность: {air_humidity}% (норма: {HUMIDITY_MIN}-{HUMIDITY_MAX}%)")
            except ValueError:
                print(f"[DEBUG]   Ошибка конвертации влажности: '{air_humidity_str}' не является числом.")
        else:
            print("[DEBUG]   Поле 'air_humidity' пустое.")

        if problem_messages:
            print("Alerter: Обнаружены проблемы, формируется оповещение...")
            subject = "🚨 Срочное оповещение от системы мониторинга"

            full_body = "Обнаружены следующие критические отклонения:\n\n"
            full_body += "\n".join(problem_messages)
            full_body += "\n\n" + "=" * 40 + "\n\nПОЛНЫЕ ДАННЫЕ:\n"
            for key, value in last_row.items():
                full_body += f"- {key.replace('_', ' ').capitalize()}: {value}\n"

            send_alert_email(subject, full_body)

            send_telegram_alert(full_body)

            with open(LAST_ALERT_STATE_FILE, 'w') as f:
                f.write(str(datetime.datetime.now().timestamp()))
        else:
            print("Alerter: Все показатели в норме.")

    finally:
        os.close(lock_fd)
        os.remove(CHECK_LOCK_FILE)


if __name__ == '__main__':
    print("--- Запуск сервиса оповещений (Alerter) ---")
    while True:
        check_and_alert()
        time.sleep(CHECK_INTERVAL_SECONDS)