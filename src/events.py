import json
import pandas as pd
from datetime import datetime, timedelta
import requests
import logging
from pathlib import Path

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Конфигурация API (исправлены протоколы)
CURRENCY_API_URL = "https://api.exchangerate-api.com/v4/latest/RUB"
STOCK_API_URL = "https://www.alphavantage.co/query"
ALPHA_VANTAGE_KEY = "sk_1234567890abcdef1234567890abcde"

def find_column(df: pd.DataFrame, possible_names: list) -> str:
    """Ищет колонку в DataFrame по списку возможных имён."""
    for name in possible_names:
        if name in df.columns:
            return name
    return None

def generate_sample_data() -> pd.DataFrame:
    """Генерирует тестовые данные при отсутствии файла."""
    sample_data = [
        {'date': '2023-12-01', 'category': 'Продукты', 'amount': -1500},
        {'date': '2023-12-02', 'category': 'Транспорт', 'amount': -250},
        {'date': '2023-12-03', 'category': 'Развлечения', 'amount': -800},
        {'date': '2023-12-04', 'category': 'Наличные', 'amount': -5000},
        {'date': '2023-12-05', 'category': 'Зарплата', 'amount': 50000}
    ]
    df = pd.DataFrame(sample_data)
    df['date'] = pd.to_datetime(df['date'])
    return df

def get_date_range(target_date: datetime, range_type: str) -> tuple:
    """Определяет диапазон дат в зависимости от типа диапазона."""
    if range_type == "W":
        start = target_date - timedelta(days=target_date.weekday())
        end = start + timedelta(days=6)
    elif range_type == "M":
        start = target_date.replace(day=1)
        end = target_date
    elif range_type == "Y":
        start = target_date.replace(month=1, day=1)
        end = target_date
    elif range_type == "ALL":
        start = datetime(1970, 1, 1)
        end = target_date
    else:
        start = target_date.replace(day=1)
        end = target_date
    return start, end

def load_transactions(file_path: str = "data/operations.xlsx") -> pd.DataFrame:
    """Загружает транзакции из Excel‑файла."""
    file = Path(file_path)
    if not file.exists():
        logger.warning(f"Файл {file_path} не найден. Используем тестовые данные.")
        return generate_sample_data()

    try:
        df = pd.read_excel(file_path)
        date_col = find_column(
            df,
            ['date', 'Дата платежа', 'Дата операции', 'transaction_date', 'payment_date']
        )
        if date_col is None:
            logger.error("Не найдена колонка с датой в данных транзакций. Доступные колонки: %s", df.columns.tolist())
            return pd.DataFrame()
        logger.info(f"Найдена колонка с датой: '{date_col}' → переименована в 'date'")
        df.rename(columns={date_col: 'date'}, inplace=True)
        df['date'] = pd.to_datetime(df['date'], errors='coerce')
        # Удаляем строки с некорректными датами
        df = df.dropna(subset=['date'])
        return df
    except Exception as e:
        logger.error(f"Ошибка загрузки транзакций: {e}")
        return pd.DataFrame()

def analyze_expenses(df: pd.DataFrame) -> dict:
    """Анализирует расходы: общие суммы и разбивку по категориям."""
    if df.empty:
        return {"total_amount": 0, "main": [], "transfers_and_cash": []}

    expenses_df = df[df['amount'] < 0].copy()
    if expenses_df.empty:
        return {"total_amount": 0, "main": [], "transfers_and_cash": []}
    expenses_df['amount'] = abs(expenses_df['amount'])

    total_amount = int(expenses_df['amount'].sum())
    main_categories = expenses_df[~expenses_df['category'].isin(['Наличные', 'Переводы'])]
    main_grouped = main_categories.groupby('category')['amount'].sum().nlargest(7)


    if len(main_grouped) > 7:
        top_7 = main_grouped.head(6)
        others_sum = main_grouped.tail(len(main_grouped) - 6).sum()
        main_data = [{"category": cat, "amount": int(amount)} for cat, amount in top_7.items()]
        main_data.append({"category": "Остальное", "amount": int(others_sum)})
    else:
        main_data = [{"category": cat, "amount": int(amount)} for cat, amount in main_grouped.items()]

    transfers_and_cash = expenses_df[expenses_df['category'].isin(['Наличные', 'Переводы'])]
    tac_grouped = transfers_and_cash.groupby('category')['amount'].sum()
    tac_data = [{"category": cat, "amount": int(amount)} for cat, amount in tac_grouped.items()]
    tac_data.sort(key=lambda x: x['amount'], reverse=True)

    return {
        "total_amount": total_amount,
        "main": main_data,
        "transfers_and_cash": tac_data
    }

def analyze_income(df: pd.DataFrame) -> dict:
    """Анализирует поступления: общую сумму и разбивку по категориям."""
    if df.empty:
        return {"total_amount": 0, "main": []}

    income_df = df[df['amount'] > 0]
    if income_df.empty:
        return {"total_amount": 0, "main": []}

    total_amount = int(income_df['amount'].sum())
    income_grouped = income_df.groupby('category')['amount'].sum().nlargest(10)
    income_data = [{"category": cat, "amount": int(amount)} for cat, amount in income_grouped.items()]

    return {"total_amount": total_amount, "main": income_data}

def get_currency_rates() -> list:
    """Получает курсы валют."""
    try:
        response = requests.get(CURRENCY_API_URL)
        response.raise_for_status()  # Проверяем HTTP‑статус: вызовет исключение для кодов 4xx/5xx

        data = response.json()

        if 'rates' not in data:
            logger.error("В ответе API не найден ключ 'rates'")
            return []

        rates = data['rates']
        result = []

        for currency in ['USD', 'EUR']:
            if currency in rates:
                result.append({
                    "currency": currency,
                    "rate": round(rates[currency], 2)
                })
            else:
                logger.warning(f"Курс для валюты {currency} не найден в ответе API")

        return result

    except requests.exceptions.RequestException as e:
        logger.error(f"Ошибка запроса к API курсов валют: {e}")
        return []
    except json.JSONDecodeError as e:
        logger.error(f"Ошибка парсинга JSON от API курсов валют: {e}")
        return []
    except Exception as e:
        logger.error(f"Неожиданная ошибка при получении курсов валют: {e}")
        return []
