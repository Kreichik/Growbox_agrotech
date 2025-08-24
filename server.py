#!/usr/bin/env python3
from flask import Flask, request,make_response,Response, jsonify, render_template
import csv
import datetime
import os
from flask import send_file
from flask_cors import CORS
import requests
from collections import deque
from dotenv import load_dotenv
from chatbot_utils import completeChat

app = Flask(__name__)

data_folder = 'box_data'
EXPECTED_DEVICES = ["esp1"]

load_dotenv()
file_path = os.getenv("SYSTEM_PROMPT_FILE")

with open(file_path, "r", encoding="utf-8") as f:
    SYSTEM_PROMPT_BASE = f.read()
lat = os.getenv("LAT")
lon = os.getenv("SYSTEM_PROMPT_BASE")
# sensor_data_buffer = {}
# buffer_lock = threading.Lock()





url = (
    "https://api.open-meteo.com/v1/forecast"
    f"?latitude={lat}&longitude={lon}"
    "&current_weather=true"
)

response_weather = requests.get(url)

try:
    response_weather = requests.get(url, timeout=10)
    if response_weather.status_code == 200:
        data = response_weather.json()
        current = data.get("current_weather", {})
        print("Температура:", current.get("temperature"), "°C")
        print("Скорость ветра:", current.get("windspeed"), "км/ч")
        print("Направление ветра:", current.get("winddirection"), "°")
        print("Погодный код (weathercode):", current.get("weathercode"))
        print("Время измерения:", current.get("time"))
    else:
        print("Ошибка при запросе погоды при старте:", response_weather.status_code)
except requests.exceptions.RequestException as e:
    print(f"ОШИБКА: Не удалось получить данные о погоде при старте. Причина: {e}")

os.makedirs('box_data', exist_ok=True)
CSV_HEADERS = [
    "timestamp", "device_id",
    "soil1", "soil2", "soil3", "soil4", "soil5",
    "ph_level", "ec", "tds", "turbidity", "co2",
    "air_temperature",
    "air_humidity",
    "water_temperature",
    "light_level"
]


CORS(app, resources={r"/api/*": {"origins": "*"}})


def get_growbox_data_for_date(date_str=None):
    def safe_float(val, default=0.0):
        try:
            return float(val) if val else default
        except (ValueError, TypeError):
            return default

    is_historical = False
    requested_date = date_str if date_str and date_str != 'now' else None

    filename_date = requested_date or datetime.datetime.now().strftime("%Y-%m-%d")
    csv_filename = os.path.join(data_folder, f'{filename_date}.csv')

    if not os.path.isfile(csv_filename):
        print(f"Файл данных не найден: {csv_filename}")
        return None, requested_date is not None, requested_date

    try:
        with open(csv_filename, 'r', newline='') as csvfile:
            reader = csv.DictReader(csvfile)
            all_rows = list(reader)

        if not all_rows:
            return None, requested_date is not None, requested_date

        last_row_in_file = all_rows[-1]

        if requested_date:
            is_historical = True
            fields_to_average = [
                "soil1", "soil2", "soil3", "soil4", "soil5",
                "ph_level", "ec", "tds", "turbidity", "co2",
                "air_temperature", "air_humidity", "light_level", "water_temperature"
            ]
            sums = {field: 0.0 for field in fields_to_average}
            count = len(all_rows)

            for row in all_rows:
                for field in fields_to_average:
                    sums[field] += safe_float(row.get(field))

            data = {field: (sums[field] / count) for field in fields_to_average}
            data["timestamp"] = last_row_in_file.get("timestamp")

        else:
            is_historical = False
            data = {key: safe_float(val) for key, val in last_row_in_file.items() if key != 'timestamp'}
            data["timestamp"] = last_row_in_file.get("timestamp")

        return data, is_historical, requested_date

    except Exception as e:
        print(f"Ошибка при чтении данных из {csv_filename}: {e}")
        return None, requested_date is not None, requested_date

@app.route('/api/<path:path>', methods=['OPTIONS', 'GET', 'POST', 'PUT', 'DELETE'])
def proxy(path):
    if request.method == 'OPTIONS':
        resp = make_response()
        resp.headers.update({
            'Access-Control-Allow-Origin': '*',
            'Access-Control-Allow-Methods': 'GET,POST,PUT,DELETE,OPTIONS',
            'Access-Control-Allow-Headers': 'Content-Type,Authorization'
        })
        return resp

    url = f'http://10.1.10.144:8080/{path}'
    resp = requests.request(
        method=request.method,
        url=url,
        headers={k: v for k, v in request.headers if k != 'Host'},
        json=request.get_json(silent=True)
    )

    excluded = ['content-encoding', 'content-length', 'transfer-encoding', 'connection']
    headers = [(k, v) for k, v in resp.raw.headers.items() if k.lower() not in excluded]

    return Response(resp.content, resp.status_code, headers)

@app.route('/sensor/data', methods=['POST'])
def receive_sensor_data():
    try:
        data = request.json
        print(f"Получены данные: {data}")
        if not data or "device_id" not in data:
            return jsonify({"error": "Invalid request format or missing device_id"}), 400

        device_id = data["device_id"]
        if device_id not in EXPECTED_DEVICES:
            return jsonify({"error": f"Unknown device: {device_id}"}), 400


        timestamp = datetime.datetime.now().isoformat()

        row = [
            timestamp,
            data.get("device_id", ""),
            data.get("soil1", ""),
            data.get("soil2", ""),
            data.get("soil3", ""),
            data.get("soil4", ""),
            data.get("soil5", ""),
            data.get("ph_level", ""),
            data.get("ec", ""),
            data.get("tds", ""),
            data.get("turbidity", ""),
            data.get("co2", ""),
            data.get("temperature", ""),
            data.get("humidity", ""),
            "",
            data.get("light_level", "")
        ]

        current_date = datetime.datetime.now().strftime("%Y-%m-%d")
        csv_filename = f'box_data/{current_date}.csv'

        file_exists = os.path.isfile(csv_filename)

        with open(csv_filename, 'a', newline='') as csvfile:
            writer = csv.writer(csvfile)
            if not file_exists:
                writer.writerow(CSV_HEADERS)
            writer.writerow(row)

        print(f"Записаны данные в {csv_filename}: {row}")

        return jsonify({"message": "Data stored successfully"}), 201

    except Exception as e:
        print(f"Ошибка при обработке данных датчика: {e}")
        return jsonify({"error": "Failed to process request"}), 500



@app.route('/sensor/data_experiment', methods=['POST'])
def receive_sensor_data_experiment():
    try:
        data = request.json
        print(f"Получены данные: {data}")
        if not data or "device_id" not in data:
            return jsonify({"error": "Invalid request format or missing device_id"}), 400

        device_id = data["device_id"]
        if device_id not in EXPECTED_DEVICES:
            return jsonify({"error": f"Unknown device: {device_id}"}), 400


        timestamp = datetime.datetime.now().isoformat()

        row = [
            timestamp,
            data.get("device_id", ""),
            data.get("soil1", ""),
            data.get("soil2", ""),
            data.get("soil3", ""),
            data.get("soil4", ""),
            data.get("soil5", ""),
            data.get("ph_level", ""),
            data.get("ec", ""),
            data.get("tds", ""),
            data.get("turbidity", ""),
            data.get("co2", ""),
            data.get("temperature", ""),
            data.get("humidity", ""),
            "",
            data.get("light_level", "")
        ]

        current_date = datetime.datetime.now().strftime("%Y-%m-%d")
        csv_filename = f'experiment/{current_date}.csv'

        file_exists = os.path.isfile(csv_filename)

        with open(csv_filename, 'a', newline='') as csvfile:
            writer = csv.writer(csvfile)
            if not file_exists:
                writer.writerow(CSV_HEADERS)
            writer.writerow(row)

        print(f"Записаны данные в {csv_filename}: {row}")

        return jsonify({"message": "Data stored successfully"}), 201

    except Exception as e:
        print(f"Ошибка при обработке данных датчика: {e}")
        return jsonify({"error": "Failed to process request"}), 500

@app.route('/update', methods=['GET'])
def check_update():
    try:
        with open("status.txt", "r") as file:
            status = file.read().strip()
            if status == "1":
                return jsonify({"update_available": True}), 200
            else:
                return jsonify({"update_available": False}), 200
    except FileNotFoundError:
        return jsonify({"update_available": False}), 200

@app.route('/firmware1', methods=['GET'])
def get_firmware1():
    firmware_path = "/home/iot/Desktop/CoAP_IOT/BlackBox.ino.bin"

    try:
        return send_file(firmware_path, as_attachment=True)
    except Exception as e:
        print(f"Ошибка при отправке файла: {e}")
        return jsonify({"error": "Failed to send firmware file"}), 500

@app.route('/firmware2', methods=['GET'])
def get_firmware2():
    firmware_path = "/home/iot/Desktop/CoAP_IOT/soil_humi_temp.ino.bin"

    try:
        return send_file(firmware_path, as_attachment=True)
    except Exception as e:
        print(f"Ошибка при отправке файла: {e}")
        return jsonify({"error": "Failed to send firmware file"}), 500


@app.route('/firmwareexperiment', methods=['GET'])
def get_firmware_experiment():
    firmware_path = "/home/iot/Desktop/CoAP_IOT/soil_humi_temp.ino.bin"

    try:
        return send_file(firmware_path, as_attachment=True)
    except Exception as e:
        print(f"Ошибка при отправке файла: {e}")
        return jsonify({"error": "Failed to send firmware file"}), 500

@app.route('/firmware/status', methods=['GET'])
def get_firmware_status():
    print("Succesfull")
    return jsonify({"message": True}), 200

@app.route('/dashboard')
def dashboard():
    return render_template('dashboard.html')

@app.route('/dashboard-new')
def new_dashboard():
    return render_template('new_dashboard.html')

@app.route('/data')
def get_data():
    data_folder = 'box_data'
    response_weather = requests.get(url)

    current = {}
    try:
        response_weather = requests.get(url, timeout=10)
        response_weather.raise_for_status()
        data = response_weather.json()
        current = data.get("current_weather", {})
    except requests.exceptions.RequestException as e:
        print(f"ОШИБКА: Не удалось получить данные о погоде. Причина: {e}")

    current_date = datetime.datetime.now().strftime("%Y-%m-%d")
    csv_filename = f'{data_folder}/{current_date}.csv'

    # csv_filename = f'2025-04-11.csv'

    if not os.path.isfile(csv_filename):
        return jsonify({"error": "No data available"}), 404

    # # Calculate the time threshold for 15 minutes ago
    # fifteen_minutes_ago = datetime.datetime.now() - datetime.timedelta(minutes=5)
    #
    # humidity_data = []
    # temperature_data = []
    # last_row = None
    #
    # with open(csv_filename, 'r') as csvfile:
    #     reader = csv.DictReader(csvfile)
    #     for row in reader:
    #         # Parse the timestamp and compare with the threshold
    #         timestamp = datetime.datetime.fromisoformat(row["timestamp"])
    #         if timestamp >= fifteen_minutes_ago:
    #             humidity_data.append({
    #                 "timestamp": row["timestamp"],
    #                 "air_humidity": float(row["air_humidity"]) if row["air_humidity"] else 0
    #             })
    #             temperature_data.append({
    #                 "timestamp": row["timestamp"],
    #                 "air_temperature": float(row["air_temperature"]) if row["air_temperature"] else 0
    #             })
    #         last_row = row

    fifteen_minutes_ago = datetime.datetime.now() - datetime.timedelta(minutes=5)

    co2_data = []
    last_row = None





    with open(csv_filename, 'r') as csvfile:
        reader = csv.DictReader(csvfile)
        last_rows = deque(reader, maxlen=10)
    humidity_data = [
        {
            "timestamp": row["timestamp"],
            "air_humidity": float(row["air_humidity"]) if row["air_humidity"] else 0
        }
        for row in last_rows
    ]

    temperature_data = [
        {
            "timestamp": row["timestamp"],
            "air_temperature": float(row["air_temperature"]) if row["air_temperature"] else 0
        }
        for row in last_rows
    ]

    co2_data = [
        {
            "timestamp": row["timestamp"],
            "co2": float(row["co2"]) if row["co2"] else 0
        }
        for row in last_rows
    ]

    turbidity_data = [
        {
            "timestamp": row["timestamp"],
            "turbidity": float(row["turbidity"]) if row["turbidity"] else 0
        }
        for row in last_rows
    ]
    ec_data = [
        {
            "timestamp": row["timestamp"],
            "ec": float(row["ec"]) if row["ec"] else 0
        }
        for row in last_rows
    ]
    tds_data = [
        {
            "timestamp": row["timestamp"],
            "tds": float(row["tds"]) if row["tds"] else 0
        }
        for row in last_rows
    ]

    last_row = last_rows[-1]


    if last_row is None:
        return jsonify({"error": "No data available"}), 404

    last_timestamp = last_row["timestamp"]
    try:
        last_ts_dt = datetime.datetime.fromisoformat(last_timestamp)
    except ValueError:
        return jsonify({"error": "Invalid last timestamp format"}), 400


    forecast_filename_temp = 'forecast_temperature.csv'
    if not os.path.isfile(forecast_filename_temp):
        return jsonify({"error": "No forecast data available"}), 404

    forecast_data_temp = []
    with open(forecast_filename_temp, 'r', newline='') as csvfile:
        reader = csv.DictReader(csvfile)
        start_collect = False
        for row in reader:
            ts_str = row.get("timestamp", "").strip()
            if not ts_str:
                continue

            try:
                forecast_ts = datetime.datetime.fromisoformat(ts_str)
            except ValueError:
                continue

            if not start_collect:
                delta = abs((forecast_ts - last_ts_dt).total_seconds())
                if delta <= 10:
                    start_collect = True

            if start_collect:
                temp = row.get("forecast_temperature", row.get("air_temperature", "0"))
                forecast_data_temp.append({
                    "timestamp": ts_str,
                    "forecast_temperature": float(temp) if temp else 0
                })
                if len(forecast_data_temp) >= 10:
                    break

    forecast_filename_hum = 'forecast_humidity.csv'
    if not os.path.isfile(forecast_filename_hum):
        return jsonify({"error": "No forecast data available"}), 404

    forecast_data_hum = []
    with open(forecast_filename_hum, 'r', newline='') as csvfile:
        reader = csv.DictReader(csvfile)
        start_collect = False
        for row in reader:
            ts_str = row.get("timestamp", "").strip()
            if not ts_str:
                continue

            try:
                forecast_ts = datetime.datetime.fromisoformat(ts_str)
            except ValueError:
                continue

            if not start_collect:
                delta = abs((forecast_ts - last_ts_dt).total_seconds())
                if delta <= 10:
                    start_collect = True

            if start_collect:
                temp = row.get("forecast_humidity", row.get("air_humidity", "0"))
                forecast_data_hum.append({
                    "timestamp": ts_str,
                    "forecast_humidity": float(temp) if temp else 0
                })
                if len(forecast_data_hum) >= 10:
                    break

    max_dates = 10

    box_data_folder = 'box_data'
    available_dates = []
    if os.path.isdir(box_data_folder):
        for fname in os.listdir(box_data_folder):
            if fname.lower().endswith('.csv'):
                date_part = fname[:-4]
                try:
                    datetime.datetime.strptime(date_part, '%Y-%m-%d')
                    available_dates.append(date_part)
                except ValueError:
                    continue
        available_dates.sort(reverse=True)
        available_dates = available_dates[:max_dates]
    else:
        available_dates = []
    data = {
        "soil1": float(last_row["soil1"]) if last_row["soil1"] else 0,
        "soil2": float(last_row["soil2"]) if last_row["soil2"] else 0,
        "soil3": float(last_row["soil3"]) if last_row["soil3"] else 0,
        "soil4": float(last_row["soil4"]) if last_row["soil4"] else 0,
        "soil5": float(last_row["soil5"]) if last_row["soil5"] else 0,
        "ph_level": float(last_row["ph_level"]) if last_row["ph_level"] else 0,
        "ec": float(last_row["ec"]) if last_row["ec"] else 0,
        "tds": float(last_row["tds"]) if last_row["tds"] else 0,
        "turbidity": float(last_row["turbidity"]) if last_row["turbidity"] else 0,
        "co2": float(last_row["co2"]) if last_row["co2"] else 0,
        "air_temperature": float(last_row["air_temperature"]) if last_row["air_temperature"] else 0,
        "air_humidity": float(last_row["air_humidity"]) if last_row["air_humidity"] else 0,
        "light_level": float(last_row["light_level"]) if last_row["light_level"] else 0,
        "water_temperature": float(last_row["water_temperature"]) if last_row["water_temperature"] else 0,
        "humidity_data": humidity_data,
        "temperature_data": temperature_data,
        "co2_data": co2_data,
        "turbidity_data": turbidity_data,
        "ec_data": ec_data,
        "tds_data": tds_data,
        "weather_temp": current.get("temperature"),
        "temperature_data_prediction": forecast_data_temp,
        "humidity_data_prediction": forecast_data_hum,
        "history_data": available_dates
    }

    return jsonify(data)

@app.route('/data_by_date')
def data_by_date():
    date_str = request.args.get('date')
    if not date_str:
        return jsonify({"error": "Параметр 'date' обязателен (формат YYYY-MM-DD)"}), 400

    try:
        datetime.datetime.strptime(date_str, '%Y-%m-%d')
    except ValueError:
        return jsonify({"error": f"Неверный формат даты: {date_str}. Ожидается YYYY-MM-DD."}), 400

    csv_filename = os.path.join(data_folder, f'{date_str}.csv')
    if not os.path.isfile(csv_filename):
        return jsonify({"error": f"Нет данных за дату {date_str}"}), 404

    # weather_url = 'ВАШ_URL_ПОГОДЫ'
    # response_weather = requests.get(weather_url)
    # if response_weather.status_code == 200:
    #     weather_json = response_weather.json()
    #     current_weather = weather_json.get("current_weather", {})
    # else:
    current_weather = {}

    with open(csv_filename, 'r', newline='') as csvfile:
        reader = csv.DictReader(csvfile)
        all_rows = list(reader)

    if not all_rows:
        return jsonify({"error": "Файл пустой или некорректный формат"}), 404

    def safe_float(val):
        try:
            return float(val)
        except (ValueError, TypeError):
            return 0.0

    fields_to_average = [
        "soil1", "soil2", "soil3", "soil4", "soil5",
        "ph_level", "air_temperature", "air_humidity", "light_level"
    ]
    sums = {field: 0.0 for field in fields_to_average}
    count = len(all_rows)

    for row in all_rows:
        for field in fields_to_average:
            sums[field] += safe_float(row.get(field, 0))

    averages = {field: (sums[field] / count) for field in fields_to_average}

    N = len(all_rows)
    step = max(1, N // 10)
    sampled_rows = []
    for i in range(10):
        idx = i * step
        if idx >= N:
            idx = N - 1
        sampled_rows.append(all_rows[idx])

    humidity_data = [
        {
            "timestamp": row["timestamp"],
            "air_humidity": safe_float(row.get("air_humidity", 0))
        }
        for row in sampled_rows
    ]

    temperature_data = [
        {
            "timestamp": row["timestamp"],
            "air_temperature": safe_float(row.get("air_temperature", 0))
        }
        for row in sampled_rows
    ]

    co2_data = [
        {
            "timestamp": row["timestamp"],
            "co2": safe_float(row.get("co2", 0))
        }
        for row in sampled_rows
    ]

    turbidity_data = [
        {
            "timestamp": row["timestamp"],
            "turbidity": safe_float(row.get("turbidity", 0))
        }
        for row in sampled_rows
    ]

    ec_data = [
        {
            "timestamp": row["timestamp"],
            "ec": safe_float(row.get("ec", 0))
        }
        for row in sampled_rows
    ]

    tds_data = [
        {
            "timestamp": row["timestamp"],
            "tds": safe_float(row.get("tds", 0))
        }
        for row in sampled_rows
    ]

    last_row = all_rows[-1]

    max_dates = 5

    box_data_folder = 'box_data'
    available_dates = []
    if os.path.isdir(box_data_folder):
        for fname in os.listdir(box_data_folder):
            if fname.lower().endswith('.csv'):
                date_part = fname[:-4]
                try:
                    datetime.datetime.strptime(date_part, '%Y-%m-%d')
                    available_dates.append(date_part)
                except ValueError:
                    continue
        available_dates.sort(reverse=True)
        available_dates = available_dates[:max_dates]
    else:
        available_dates = []

    result = {
        "soil1": averages["soil1"],
        "soil2": averages["soil2"],
        "soil3": averages["soil3"],
        "soil4": averages["soil4"],
        "soil5": averages["soil5"],
        "ph_level": averages["ph_level"],
        "air_temperature": averages["air_temperature"],
        "air_humidity": averages["air_humidity"],
        "light_level": averages["light_level"],

        "co2": safe_float(last_row.get("co2", 0)),
        "turbidity": safe_float(last_row.get("turbidity", 0)),
        "ec": safe_float(last_row.get("ec", 0)),
        "tds": safe_float(last_row.get("tds", 0)),

        "humidity_data": humidity_data,
        "temperature_data": temperature_data,
        "co2_data": co2_data,
        "turbidity_data": turbidity_data,
        "ec_data": ec_data,
        "tds_data": tds_data,

        "weather_temp": current_weather.get("temperature"),

        "temperature_data_prediction": None,
        "humidity_data_prediction": None,

        "history_data": available_dates
    }

    return jsonify(result), 200
@app.route('/monitor')
def monitor():
    current_date = datetime.datetime.now().strftime("%Y-%m-%d")
    csv_filename = f'{data_folder}/{current_date}.csv'

    if not os.path.isfile(csv_filename):
        return "No data available", 404

    last_row = None
    with open(csv_filename, 'r') as csvfile:
        reader = csv.DictReader(csvfile)
        for row in reader:
            last_row = row

    if last_row is None:
        return "No data available", 404

    return render_template('monitor.html', data=last_row)


@app.route('/monitor-data')
def monitor_data():
    current_date = datetime.datetime.now().strftime("%Y-%m-%d")
    csv_filename = f'{data_folder}/{current_date}.csv'

    if not os.path.isfile(csv_filename):
        return jsonify({"error": "No data available"}), 404

    last_row = None
    with open(csv_filename, 'r') as csvfile:
        reader = csv.DictReader(csvfile)
        for row in reader:
            last_row = row

    if last_row is None:
        return jsonify({"error": "No data available"}), 404

    return jsonify(last_row)

@app.route('/data-status')
def data_status():
    return jsonify({"message": True})

@app.route('/login')
def login_page():
    return render_template('login_page.html')

@app.route('/journal')
def journal_form():
    return render_template('journal_form.html')

@app.route('/history')
def journal_history():
    return render_template('journal_history.html')


@app.route('/chat', methods=['POST'])
def chat():
    try:
        data = request.json
        user_input = data.get("message", "")
        history = data.get("history", [])
        date_context = data.get("date_context")
        last_context_timestamp = data.get("last_context_timestamp")

        if not user_input:
            return jsonify({"error": "Empty message"}), 400

        current_data, is_historical, requested_date = get_growbox_data_for_date(date_context)

        current_request_time = datetime.datetime.now().isoformat(timespec='seconds')

        data_context_block = "\n<CURRENT_DATA>\n"
        data_context_block += f"info: Текущее время запроса: {current_request_time}\n"

        if current_data:
            data_header = "type: Средние показатели за день" if is_historical else "type: Текущие показатели"
            real_timestamp = current_data.get("timestamp", "неизвестно")

            data_context_block += f"{data_header}\n"
            data_context_block += f"timestamp: {real_timestamp}\n\n"

            data_context_block += f"air_temperature: {current_data['air_temperature']:.1f}\n"
            data_context_block += f"air_humidity: {current_data['air_humidity']:.1f}\n"
            data_context_block += f"co2: {current_data['co2']:.0f}\n"
            data_context_block += f"light_level: {current_data['light_level']:.0f}\n"
            data_context_block += f"soil_moisture: {current_data['soil1']:.0f}, {current_data['soil2']:.0f}, {current_data['soil3']:.0f}, {current_data['soil4']:.0f}, {current_data['soil5']:.0f}\n"
            data_context_block += f"ph_level: {current_data['ph_level']:.2f}\n"
            data_context_block += f"ec: {current_data['ec']:.2f}\n"
            data_context_block += f"tds: {current_data['tds']:.0f}\n"
            data_context_block += f"turbidity: {current_data['turbidity']:.0f}\n"

        else:
            date_info = f"за {requested_date}" if requested_date else "на текущий момент"
            data_context_block += f"status: Данные недоступны {date_info}."

        data_context_block += "\n</CURRENT_DATA>"
        greeting_instruction = ""
        new_timestamp_for_client = None

        if current_data:
            new_timestamp_for_client = current_data.get("timestamp")

            if new_timestamp_for_client != last_context_timestamp:
                context_description = "средние данные за " + requested_date if is_historical else "текущие показатели"
                greeting_instruction = f"Всегда начинай свой ответ с фразы 'Анализирую {context_description}...'. Это приказ."
            else:
                greeting_instruction = "Просто отвечай на вопрос пользователя без лишних вступлений. Не используй фразу 'Анализирую...'."

        final_system_prompt = SYSTEM_PROMPT_BASE.format(GREETING_INSTRUCTION=greeting_instruction)
        final_system_prompt += data_context_block

        messages_to_send = [
            {"role": "system", "content": final_system_prompt}
        ]
        messages_to_send.extend(history)

        response_text = completeChat(prompt=user_input, history=messages_to_send)

        return jsonify({
            "reply": response_text,
            "new_context_timestamp": new_timestamp_for_client
        })

    except Exception as e:
        print(f"Chat error: {e}")
        return jsonify({"error": "Failed to get reply"}), 500

def get_latest_growbox_data():
    current_date = datetime.datetime.now().strftime("%Y-%m-%d")
    csv_filename = f'box_data/{current_date}.csv'

    if not os.path.isfile(csv_filename):
        print(f"Файл данных за сегодня ({csv_filename}) не найден.")
        return None

    try:
        with open(csv_filename, 'r') as csvfile:
            reader = csv.DictReader(csvfile)
            last_row = None
            for row in reader:
                last_row = row

        if not last_row:
            return None

        data = {
            "soil1": float(last_row.get("soil1") or 0),
            "soil2": float(last_row.get("soil2") or 0),
            "soil3": float(last_row.get("soil3") or 0),
            "soil4": float(last_row.get("soil4") or 0),
            "soil5": float(last_row.get("soil5") or 0),
            "ph_level": float(last_row.get("ph_level") or 0),
            "ec": float(last_row.get("ec") or 0),
            "tds": float(last_row.get("tds") or 0),
            "turbidity": float(last_row.get("turbidity") or 0),
            "co2": float(last_row.get("co2") or 0),
            "air_temperature": float(last_row.get("air_temperature") or 0),
            "air_humidity": float(last_row.get("air_humidity") or 0),
            "light_level": float(last_row.get("light_level") or 0),
            "water_temperature": float(last_row.get("water_temperature") or 0),
            "timestamp": last_row.get("timestamp")
        }
        return data
    except Exception as e:
        print(f"Ошибка при чтении данных из CSV: {e}")
        return None

if __name__ == '__main__':
    is_debug_mode = os.environ.get("FLASK_ENV") == "development"
    if is_debug_mode:
        print("--- Запуск Flask в режиме ОТЛАДКИ (DEBUG) ---")
        app.run(host='0.0.0.0', port=5000, debug=True)
    else:

        print("--- Скрипт готов для запуска через WSGI-сервер (Gunicorn) ---")