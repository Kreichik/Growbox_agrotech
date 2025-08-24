import pandas as pd
import numpy as np
from sklearn.preprocessing import MinMaxScaler
from statsmodels.tsa.arima.model import ARIMA
from tcn import TCN
from tensorflow.keras.models import Sequential
from tensorflow.keras.layers import Dense, Input
import os # Добавим импорт os для проверки файла

# Параметры
INPUT_LEN = 600
FORECAST_STEPS = 1200
# Длина данных для обучения ARIMA (например, такая же как INPUT_LEN, или больше/меньше)
ARIMA_TRAIN_LEN = 600
CSV_FILENAME = '2025-04-11.csv' # Убедитесь, что файл в текущей директории или укажите полный путь

# --- 1. Загрузка и подготовка ВСЕХ данных ---
try:
    df_full = pd.read_csv(CSV_FILENAME, parse_dates=['timestamp'])
except FileNotFoundError:
    print(f"Ошибка: Файл не найден: {CSV_FILENAME}")
    exit() # Выход из скрипта, если файла нет

df_full.set_index('timestamp', inplace=True)
df_full = df_full[['air_temperature', 'air_humidity']].dropna()

# Проверка достаточного количества данных для ВСЕГО процесса
# Нам нужно как минимум ARIMA_TRAIN_LEN + INPUT_LEN для ARIMA и TCN предсказания
# и еще FORECAST_STEPS для создания хотя бы одного y_tcn
min_total_len = max(ARIMA_TRAIN_LEN, INPUT_LEN) + FORECAST_STEPS
# Или, если ARIMA обучается до TCN входа: ARIMA_TRAIN_LEN + INPUT_LEN + FORECAST_STEPS
# Для цикла TCN нужно хотя бы INPUT_LEN + FORECAST_STEPS точек
min_tcn_loop_len = INPUT_LEN + FORECAST_STEPS

if len(df_full) < min_tcn_loop_len:
    print(f"Ошибка: Недостаточно данных в файле ({len(df_full)}).")
    print(f"Требуется как минимум {min_tcn_loop_len} точек для создания обучающих выборок TCN.")
    exit()

# Попытка установить частоту индекса (убирает предупреждения statsmodels)
inferred_freq = pd.infer_freq(df_full.index)
if inferred_freq:
    print(f"Определена частота данных: {inferred_freq}")
    df_full.index.freq = inferred_freq
elif (df_full.index.to_series().diff().mode() == pd.Timedelta(seconds=6)).any(): # Проверка, если основная частота 6 сек
     print("Установка предполагаемой частоты '6S'")
     try:
         df_full.index.freq = '6S'
     except ValueError:
         print("Предупреждение: Не удалось установить частоту '6S', индекс может быть нерегулярным.")
else:
    print("Предупреждение: Не удалось определить частоту данных. Forecasting ARIMA может использовать числовые индексы.")


# --- 2. ARIMA ---
print("Подготовка и обучение ARIMA...")
# Данные для ARIMA: берем ARIMA_TRAIN_LEN точек ПЕРЕД последними INPUT_LEN
if len(df_full) >= ARIMA_TRAIN_LEN + INPUT_LEN:
    arima_train_data = df_full['air_temperature'].iloc[-(ARIMA_TRAIN_LEN + INPUT_LEN):-INPUT_LEN]
    print(f"Используется {len(arima_train_data)} точек для обучения ARIMA.")
elif len(df_full) > INPUT_LEN:
     arima_train_data = df_full['air_temperature'].iloc[:-INPUT_LEN]
     print(f"Предупреждение: Данных меньше, чем ARIMA_TRAIN_LEN + INPUT_LEN. Используется {len(arima_train_data)} точек для обучения ARIMA.")
else:
    arima_train_data = pd.Series([]) # Пустой Series
    print("Ошибка: Недостаточно данных для выделения обучающей выборки ARIMA.")

arima_preds = None
if len(arima_train_data) >= 10: # Минимальный порог для ARIMA
    try:
        # Передаем данные с возможно установленной частотой
        arima_model = ARIMA(arima_train_data, order=(3,1,2)).fit()
        # Прогнозируем на FORECAST_STEPS шагов вперед
        arima_preds = arima_model.forecast(steps=FORECAST_STEPS)
        print("ARIMA модель обучена и прогноз сделан.")
    except (np.linalg.LinAlgError, ValueError, Exception) as e: # Ловим больше ошибок
        print(f"Ошибка при обучении или прогнозировании ARIMA: {e}")
        print("Прогноз ARIMA будет пропущен.")
else:
    print("Слишком мало данных для обучения ARIMA. Пропускаем.")

# --- 3. TCN ---
print("Подготовка данных и обучение TCN...")
scaler = MinMaxScaler()
# Масштабируем ВЕСЬ доступный набор данных
scaled_full = scaler.fit_transform(df_full)

X_tcn, y_tcn = [], []
# Цикл по масштабированным полным данным для создания обучающих выборок
# Должно быть достаточно данных: len(scaled_full) >= INPUT_LEN + FORECAST_STEPS
num_samples_possible = len(scaled_full) - INPUT_LEN - FORECAST_STEPS + 1
if num_samples_possible > 0:
    print(f"Создание {num_samples_possible} обучающих выборок для TCN...")
    for i in range(num_samples_possible):
        X_tcn.append(scaled_full[i : i + INPUT_LEN])
        # y должен содержать FORECAST_STEPS точек для КАЖДОГО из признаков
        y_tcn.append(scaled_full[i + INPUT_LEN : i + INPUT_LEN + FORECAST_STEPS])
    X_tcn, y_tcn = np.array(X_tcn), np.array(y_tcn)
    print(f"Форма X_tcn: {X_tcn.shape}, Форма y_tcn: {y_tcn.shape}") # Отладочный вывод
else:
    print(f"Ошибка: Недостаточно данных ({len(scaled_full)}) для создания хотя бы одной выборки TCN (требуется {INPUT_LEN + FORECAST_STEPS}).")
    X_tcn, y_tcn = np.array([]), np.array([]) # Создаем пустые массивы

future_pred = None # Инициализируем переменную для прогноза TCN
if X_tcn.shape[0] > 1: # Нужно хотя бы 2 выборки: одна для обучения, одна для предсказания
    X_train_tcn = X_tcn[:-1]
    # y_tcn имеет форму (n_samples, forecast_steps, n_features)
    # Преобразуем y для Dense слоя: (n_samples, forecast_steps * n_features)
    y_train_tcn = y_tcn[:-1].reshape(X_train_tcn.shape[0], -1) # Правильный reshape!

    # Последняя последовательность X для финального предсказания
    latest_input_scaled = X_tcn[-1:]

    print(f"Форма X_train_tcn: {X_train_tcn.shape}, Форма y_train_tcn: {y_train_tcn.shape}")
    print(f"Форма latest_input_scaled: {latest_input_scaled.shape}")

    # Определение и обучение модели TCN
    n_features = df_full.shape[1] # Количество признаков (2 в вашем случае)
    model_tcn = Sequential([
        Input(shape=(INPUT_LEN, n_features)),
        TCN(nb_filters=64, kernel_size=4, dilations=[1, 2, 4, 8], return_sequences=False),
        Dense(FORECAST_STEPS * n_features) # Выходной слой должен соответствовать reshape для y_train_tcn
    ])
    model_tcn.compile(optimizer='adam', loss='mse')

    print(f"Обучение TCN на {len(X_train_tcn)} выборках...")
    # Увеличьте epochs, если нужно лучшее обучение; verbose=1 для вывода прогресса
    model_tcn.fit(X_train_tcn, y_train_tcn, epochs=10, batch_size=min(32, len(X_train_tcn)), verbose=1)

    # Предсказание на последних данных
    print("Предсказание TCN...")
    future_pred_scaled = model_tcn.predict(latest_input_scaled).reshape(FORECAST_STEPS, n_features)
    future_pred = scaler.inverse_transform(future_pred_scaled)
    print("Предсказание TCN завершено.")

elif X_tcn.shape[0] == 1:
     print("Предупреждение: Только одна выборка данных для TCN. Обучение невозможно.")
     # Можно либо загрузить предобученную модель, либо пропустить TCN
     print("Прогноз TCN будет пропущен.")
     # latest_input_scaled = X_tcn[0:1] # Можно взять эту выборку, если есть модель
else:
     print("Ошибка: Недостаточно данных для обучения TCN. Прогноз TCN будет пропущен.")

# --- 4. Формирование временного индекса и сохранение результатов ---
print("Сохранение результатов...")
# Время для прогноза начинается после последней точки в ИСХОДНЫХ данных
last_time = df_full.index[-1]
future_time = pd.date_range(start=last_time + pd.Timedelta(seconds=6), periods=FORECAST_STEPS, freq='6S') # Используем '6S' если уверены

# Сохранение прогноза TCN (если он был сделан)
if future_pred is not None:
    df_forecast = pd.DataFrame(future_pred, columns=df_full.columns, index=future_time)
    df_forecast.index.name = 'timestamp'
    df_forecast[['air_temperature']].to_csv("forecast_temperature.csv")
    df_forecast[['air_humidity']].to_csv("forecast_humidity.csv")
    print("Прогнозы TCN сохранены в forecast_temperature.csv и forecast_humidity.csv")
else:
    # Создаем пустые файлы или файлы с NaN, чтобы показать отсутствие прогноза
    df_empty = pd.DataFrame(index=future_time, columns=['air_temperature'])
    df_empty.to_csv("forecast_temperature.csv")
    df_empty['air_humidity'] = np.nan # Добавляем колонку влажности
    df_empty[['air_humidity']].to_csv("forecast_humidity.csv")
    print("Файлы прогнозов TCN созданы (пустые или NaN), так как модель не была обучена/не предсказывала.")


# Сохранение прогноза ARIMA (если он был сделан)
if arima_preds is not None:
    # Убедимся, что индекс совпадает с future_time
    if len(arima_preds) == len(future_time):
         df_arima = pd.DataFrame({'air_temperature': arima_preds.values}, index=future_time)
    else:
         print(f"Предупреждение: Длина прогноза ARIMA ({len(arima_preds)}) не совпадает с длиной future_time ({len(future_time)}). Используются первые {len(future_time)} значений ARIMA.")
         # Обрезаем или дополняем NaN, здесь обрезаем
         df_arima = pd.DataFrame({'air_temperature': arima_preds.values[:len(future_time)]}, index=future_time)

    df_arima.to_csv("forecast_temperature_arima.csv")
    print("Прогноз ARIMA сохранен в forecast_temperature_arima.csv")
else:
    # Создаем пустой файл, чтобы показать отсутствие прогноза
    df_empty_arima = pd.DataFrame(index=future_time, columns=['air_temperature'])
    df_empty_arima.to_csv("forecast_temperature_arima.csv")
    print("Файл прогноза ARIMA создан (пустой), так как модель не была обучена/не предсказывала.")

print("Скрипт завершен.")