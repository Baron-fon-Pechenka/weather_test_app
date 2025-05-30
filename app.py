from flask import Flask, render_template, request, jsonify, redirect, url_for, session
from flask_session import Session
import requests
from datetime import datetime, timedelta

app = Flask(__name__)
app.config['SECRET_KEY'] = 'your-secret-key'
app.config['SESSION_TYPE'] = 'filesystem'  # Можно использовать 'redis' или другое хранилище
Session(app)

# Популярные города
POPULAR_CITIES = [
    {"name": "Москва", "latitude": 55.7558, "longitude": 37.6173, "timezone": "Europe/Moscow"},
    {"name": "Санкт-Петербург", "latitude": 59.9343, "longitude": 30.3351, "timezone": "Europe/Moscow"},
    {"name": "Новосибирск", "latitude": 55.0084, "longitude": 82.9357, "timezone": "Asia/Novosibirsk"},
    {"name": "Екатеринбург", "latitude": 56.8389, "longitude": 60.6057, "timezone": "Asia/Yekaterinburg"},
    {"name": "Казань", "latitude": 55.7961, "longitude": 49.1064, "timezone": "Europe/Moscow"},
    {"name": "Сочи", "latitude": 43.5855, "longitude": 39.7231, "timezone": "Europe/Moscow"},
    {"name": "Калининград", "latitude": 54.7104, "longitude": 20.4522, "timezone": "Europe/Kaliningrad"},
]

def get_city_suggestions(query=""):
    if not query:
        return POPULAR_CITIES
    url = "https://geocoding-api.open-meteo.com/v1/search"
    params = {
        "name": query,
        "count": 5,
        "language": "ru",
        "format": "json"
    }
    try:
        response = requests.get(url, params=params)
        response.raise_for_status()
        data = response.json()
        return [{
            "name": loc["name"],
            "latitude": loc["latitude"],
            "longitude": loc["longitude"],
            "timezone": loc["timezone"]
        } for loc in data.get("results", [])[:5]]
    except:
        return []

def get_weather_data(latitude, longitude, timezone):
    url = "https://api.open-meteo.com/v1/forecast"
    params = {
        "latitude": latitude,
        "longitude": longitude,
        "timezone": timezone,
        "current": "temperature_2m,precipitation,wind_speed_10m",
        "hourly": "precipitation_probability",
        "daily": "temperature_2m_max,temperature_2m_min,precipitation_sum,wind_speed_10m_max",
        "forecast_days": 8
    }
    try:
        response = requests.get(url, params=params)
        response.raise_for_status()
        return response.json()
    except:
        return None

def process_weather_data(data, city_name):
    if not data:
        return None

    current = data["current"]
    today_precip_prob = max(data["hourly"]["precipitation_probability"][:24])

    forecast = []
    daily = data["daily"]
    for i in range(1, 8):
        date = (datetime.now() + timedelta(days=i)).strftime("%d.%m")
        forecast.append({
            "date": date,
            "max_temp": daily["temperature_2m_max"][i],
            "min_temp": daily["temperature_2m_min"][i],
            "precipitation": daily["precipitation_sum"][i],
            "wind_speed": daily["wind_speed_10m_max"][i]
        })

    return {
        "city": city_name,
        "current": {
            "temp": current["temperature_2m"],
            "precip": current["precipitation"],
            "wind": current["wind_speed_10m"],
            "precip_prob": today_precip_prob
        },
        "forecast": forecast
    }

@app.before_request
def initialize_session():
    if 'history' not in session:
        session['history'] = {}

@app.route("/")
def index():
    last_visited = None
    if session['history']:
        last_visited = next(iter(session['history']))  # Город, который был первый в истории
    return render_template("index.html", last_visited=last_visited)

@app.route("/autocomplete", methods=["GET"])
def autocomplete():
    query = request.args.get("query", "")
    suggestions = get_city_suggestions(query)
    return jsonify(suggestions)

@app.route("/weather")
def weather():
    city_name = request.args.get("city", "").strip()
    if not city_name:
        return redirect(url_for("index"))

    # Ищем в популярных или делаем запрос
    location = next((c for c in POPULAR_CITIES if c["name"] == city_name), None)
    if not location:
        suggestions = get_city_suggestions(city_name)
        location = suggestions[0] if suggestions else None

    if not location:
        return render_template("error.html", message="Город не найден")

    # Обновляем историю
    history = session['history']
    history[city_name] = history.get(city_name, 0) + 1
    session.modified = True

    data = get_weather_data(location["latitude"], location["longitude"], location["timezone"])
    weather_info = process_weather_data(data, location["name"])

    if not weather_info:
        return render_template("error.html", message="Ошибка получения данных о погоде")

    return render_template("weather.html", weather=weather_info)

@app.route("/history")
def get_history():
    return jsonify(session['history'])

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)