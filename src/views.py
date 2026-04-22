import json
from datetime import datetime
from flask import Flask, jsonify, request
import pandas as pd
from src.utils import get_dashboard_data, get_events_data

app = Flask(__name__)

@app.route('/home', methods=['GET'])
def home_page():
    """
    Функция для страницы «Главная».
    Принимает строку с датой и временем в формате YYYY-MM-DD HH:MM:SS.
    Возвращает корректный JSON‑ответ согласно ТЗ.
    """
    # Получаем параметр даты из запроса (например, ?datetime=2023-12-25 14:30:00)
    date_string = request.args.get('datetime')

    if not date_string:
        return jsonify({"error": "Параметр datetime обязателен"}), 400

    try:
        # Проверяем формат даты
        parsed_datetime = datetime.strptime(date_string, "%Y-%m-%d %H:%M:%S")
    except ValueError:
        return jsonify({
            "error": "Неверный формат даты. Ожидаемый формат: YYYY-MM-DD HH:MM:SS"
        }), 400

    # Вызываем вспомогательную функцию из utils.py
    result_data = get_dashboard_data(parsed_datetime)

    # Возвращаем JSON‑ответ
    return jsonify(result_data)

@app.route('/events', methods=['GET'])
def events_page():
    """
    Функция для страницы «События».
    """
    try:
        # Загружаем данные из Excel
        df = pd.read_excel('data/operations.xlsx')
        if 'Дата операции' in df.columns:
            df['Дата операции'] = pd.to_datetime(df['Дата операции'])

        # Вызываем вспомогательную функцию для обработки данных
        result_data = get_events_data(df)
        return jsonify(result_data)
    except Exception as e:
        return jsonify({"error": f"Ошибка при загрузке данных: {str(e)}"}), 500

if __name__ == '__main__':
    app.run(debug=True)
