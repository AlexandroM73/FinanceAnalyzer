import json
import pandas as pd
from datetime import datetime, timedelta
import requests
import logging
from pathlib import Path

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Конфигурация API
CURRENCY_API_URL = "https://api.exchangerate-api.com/v4/latest/RUB"
STOCK_API_URL = "https://www.alphavantage.co/query"
ALPHA_VANTAGE_KEY = "your_api_key"  # Замените на реальный ключ


def get_date_range(target_date: datetime, range_type: str) -> tuple:
    """Определяет диапазон дат в зависимости от типа диапазона."""
    if range_type == "W":
        # Неделя: с понедельника по воскресенье, содержащие целевую дату
        start = target_date - timedelta(days=target_date.weekday())
        end = start + timedelta(days=6)
    elif range_type == "M":
        # Месяц: с первого числа месяца по целевую дату
        start = target_date.replace(day=1)
        end = target_date
    elif range_type == "Y":
        # Год: с 1 января года по целевую дату
        start = target_date.replace(month=1, day=1)
        end = target_date
    elif range_type == "ALL":
        # Все данные до указанной даты
        start = datetime(1970, 1, 1)  # Начало эпохи Unix
        end = target_date
    else:
        # По умолчанию — месяц
        start = target_date.replace(day=1)
        end = target_date

    return start, end


def load_transactions(file_path: str = "data/operations.xlsx") -> pd.DataFrame:
    """Загружает транзакции из Excel‑файла."""
    try:
        df = pd.read_excel(file_path)
        df['date'] = pd.to_datetime(df['date'])
        return df
    except Exception as e:
        logger.error(f"Ошибка загрузки транзакций: {e}")
        return pd.DataFrame()


def analyze_expenses(df: pd.DataFrame) -> dict:
    """Анализирует расходы: общие суммы и разбивку по категориям."""
    # Фильтруем расходы (отрицательные суммы)
    expenses_df = df[df['amount'] < 0].copy()
    expenses_df['amount'] = abs(expenses_df['amount'])  # Берём модуль суммы

    total_amount = int(expenses_df['amount'].sum())

    # Основные категории (исключая «Наличные» и «Переводы»)
    main_categories = expenses_df[~expenses_df['category'].isin(['Наличные', 'Переводы'])]
    main_grouped = main_categories.groupby('category')['amount'].sum().nlargest(7)

    # Если категорий больше 7, суммируем остальные в «Остальное»
    if len(main_grouped) > 7:
        top_7 = main_grouped.head(6)
        others_sum = main_grouped.tail(len(main_grouped) - 6).sum()
        main_data = [
            {"category": cat, "amount": int(amount)}
            for cat, amount in top_7.items()
        ]
        main_data.append({"category": "Остальное", "amount": int(others_sum)})
    else:
        main_data = [
            {"category": cat, "amount": int(amount)}
            for cat, amount in main_grouped.items()
        ]

    # Переводы и наличные
    transfers_and_cash = expenses_df[expenses_df['category'].isin(['Наличные', 'Переводы'])]
    tac_grouped = transfers_and_cash.groupby('category')['amount'].sum()
    tac_data = [
        {"category": cat, "amount": int(amount)}
        for cat, amount in tac_grouped.items()
    ]
    tac_data.sort(key=lambda x: x['amount'], reverse=True)

    return {
        "total_amount": total_amount,
        "main": main_data,
        "transfers_and_cash": tac_data
    }


def analyze_income(df: pd.DataFrame) -> dict:
    """Анализирует поступления: общую сумму и разбивку по категориям."""
    # Фильтруем поступления (положительные суммы)
    income_df = df[df['amount'] > 0]

    total_amount = int(income_df['amount'].sum())
    income_grouped = income_df.groupby('category')['amount'].sum().nlargest(10)  # Берём топ‑10

    income_data = [
        {"category": cat, "amount": int(amount)}
        for cat, amount in income_grouped.items()
    ]

    return {
        "total_amount": total_amount,
        "main": income_data
    }


def get_currency_rates() -> list:
    """Получает курсы валют."""
    try:
        response = requests.get(CURRENCY_API_URL)
        data = response.json()
        rates = data.get("rates", {})
        return [
            {"currency": currency, "rate": round(rate, 2)}
            for currency, rate in rates.items()
            if currency in ["USD", "EUR"]
        ]
    except Exception as e:
        logger.error(f"Ошибка получения курсов валют: {e}")
        return []


def get_stock_prices() -> list:
    """Получает цены акций из S&P500."""
    stocks = ["AAPL", "AMZN", "GOOGL", "MSFT", "TSLA"]
    prices = []
    for symbol in stocks:
        try:
            params = {
                "function": "GLOBAL_QUOTE",
                "symbol": symbol,
                "apikey": ALPHA_VANTAGE_KEY
            }
            response = requests.get(STOCK_API_URL, params=params)
            data = response.json()
            if "Global Quote" in data:
                price = data["Global Quote"].get("05. price")
                prices.append({
                    "stock": symbol,
                    "price": round(float(price), 2) if price else 0.0
                })
        except Exception as e:
            logger.error(f"Ошибка для акции {symbol}: {e}")
            prices.append({"stock": symbol, "price": 0.0})
    return prices


def generate_events_json(input_date: str, range_type: str = "M") -> dict:
    """
    Главная функция: принимает дату и тип диапазона, возвращает JSON‑ответ.

    Args:
        input_date (str): Дата в формате 'YYYY-MM-DD'
        range_type (str): Тип диапазона ('W', 'M', 'Y', 'ALL'). По умолчанию 'M'

    Returns:
        dict: JSON‑ответ согласно спецификации
    """
    try:
        # Парсим входную дату
        target_dt = datetime.strptime(input_date, "%Y-%m-%d")

        # Определяем диапазон дат
        start_date, end_date = get_date_range(target_dt, range_type)

        # Загружаем и фильтруем транзакции
        transactions_df = load_transactions()
        filtered_df = transactions_df[
            (transactions_df['date'] >= start_date) &
            (transactions_df['date'] <= end_date)
            ]

        # Анализируем расходы и поступления
        expenses_data = analyze_expenses(filtered_df)
        income_data = analyze_income(filtered_df)

        # Формируем ответ
        response = {
            "expenses": expenses_data,
            "income": income_data,
            "currency_rates": get_currency_rates(),
            "stock_prices": get_stock_prices()
        }
        return response
    except Exception as e:
        logger.error(f"Ошибка генерации JSON‑ответа: {e}")
        return {"error": "Произошла ошибка при обработке запроса"}


if __name__ == "__main__":
    # Пример использования
    test_date = "2023-12-21"

    print("=== Тест 1: Диапазон — месяц (по умолчанию) ===")
    result1 = generate_events_json(test_date, "M")
    print(json.dumps(result1, ensure_ascii=False, indent=2))

    print("\n=== Тест 2: Диапазон — неделя ===")
    result2 = generate_events_json(test_date, "W")
    print(json.dumps(result2, ensure_ascii=False, indent=2))

    print("\n=== Тест 3: Диапазон — год ===")
    result3 = generate_events_json(test_date, "Y")
    print(json.dumps(result3, ensure_ascii=False, indent=2))

    print("\n=== Тест 4: Диапазон — все данные до даты ===")
    result4 = generate_events_json(test_date, "ALL")
    print(json.dumps(result4, ensure_ascii=False, indent=2))

    print("\n=== Тест 5: Некорректный диапазон (должен использовать значение по умолчанию) ===")
    result5 = generate_events_json(test_date, "INVALID")
    print(json.dumps(result5, ensure_ascii=False, indent=2))
