import json
import pandas as pd
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

def get_greeting(input_datetime: str) -> str:
    """Определяет приветствие в зависимости от времени суток."""
    try:
        dt = datetime.strptime(input_datetime, "%Y-%m-%d %H:%M:%S")
        hour = dt.hour

        if 5 <= hour < 12:
            return "Доброе утро"
        elif 12 <= hour < 17:
            return "Добрый день"
        elif 17 <= hour < 23:
            return "Добрый вечер"
        else:
            return "Доброй ночи"
    except ValueError as e:
        logger.error(f"Ошибка парсинга даты: {e}")
        return "Здравствуйте"

def load_transactions_from_excel() -> pd.DataFrame:
    """Загружает транзакции из Excel‑файла с обработкой ошибок."""
    try:
        df = pd.read_excel('data/operations.xlsx')

        # Проверяем наличие обязательных столбцов
        required_columns = ['Дата операции', 'Категория', 'Сумма операции', 'Номер карты']
        missing = [col for col in required_columns if col not in df.columns]
        if missing:
            raise ValueError(f"Отсутствуют столбцы: {', '.join(missing)}")

        # Преобразуем дату
        df['Дата операции'] = pd.to_datetime(df['Дата операции'], errors='coerce')
        # Извлекаем последние 4 цифры карты
        df['card_last_digits'] = df['Номер карты'].astype(str).str[-4:]

        logger.info("Данные успешно загружены из Excel")
        return df
    except FileNotFoundError:
        logger.error("Файл data/operations.xlsx не найден")
        raise
    except Exception as e:
        logger.error(f"Ошибка при загрузке данных из Excel: {e}")
        raise

def calculate_card_stats(transactions: pd.DataFrame) -> List[Dict[str, Any]]:
    """Рассчитывает статистику по картам: последние 4 цифры, расходы, кешбэк."""
    if transactions.empty:
        return []

    # Группируем по картам (последние 4 цифры)
    card_groups = transactions.groupby('card_last_digits')
    cards_stats = []

    for card_digits, group in card_groups:
        total_spent = group['Сумма операции'].sum()
        cashback = round(total_spent / 100, 2)  # 1 рубль на каждые 100 рублей

        cards_stats.append({
            "last_digits": str(card_digits),
            "total_spent": round(total_spent, 2),
            "cashback": cashback
        })

    return cards_stats

def get_top_transactions(transactions: pd.DataFrame, top_n: int = 5) -> List[Dict[str, Any]]:
    """Получает топ‑N транзакций по сумме платежа."""
    if transactions.empty:
        return []

    # Сортируем по абсолютной величине суммы (чтобы крупные списания были вверху)
    sorted_transactions = transactions.reindex(
        transactions['Сумма операции'].abs().sort_values(ascending=False).index
    )

    top_transactions = []
    for _, row in sorted_transactions.head(top_n).iterrows():
        top_transactions.append({
            "date": row['Дата операции'].strftime("%d.%m.%Y"),
            "amount": round(row['Сумма операции'], 2),
            "category": row['Категория'],
            "description": row.get('Описание', 'Без описания')
        })

    return top_transactions

def get_currency_rates() -> List[Dict[str, Any]]:
    """Получает курсы валют (заглушка — в реальности нужно API)."""
    return [
        {"currency": "USD", "rate": 73.21},
        {"currency": "EUR", "rate": 87.08}
    ]

def get_stock_prices() -> List[Dict[str, Any]]:
    """Получает стоимость акций из S&P500 (заглушка)."""
    return [
        {"stock": "AAPL", "price": 150.12},
        {"stock": "AMZN", "price": 3173.18},
        {"stock": "GOOGL", "price": 2742.39},
        {"stock": "MSFT", "price": 296.71},
        {"stock": "TSLA", "price": 1007.08}
    ]

def main_page(input_datetime: str) -> str:
    """
    Главная функция страницы «Главная».

    Принимает строку с датой и временем в формате YYYY-MM-DD HH:MM:SS
    и возвращает JSON‑ответ с приветствием, данными по картам, топ‑транзакциями,
    курсами валют и стоимостью акций.
    """
    logger.info(f"Запрос главной страницы с датой: {input_datetime}")

    try:
        # 1. Приветствие
        greeting = get_greeting(input_datetime)

        # 2. Загружаем транзакции из Excel
        transactions = load_transactions_from_excel()

        # 3. Данные по картам
        cards = calculate_card_stats(transactions)

        # 4. Топ‑5 транзакций
        top_transactions = get_top_transactions(transactions, 5)

        # 5. Курсы валют
        currency_rates = get_currency_rates()

        # 6. Стоимость акций
        stock_prices = get_stock_prices()

        # Формируем итоговый JSON
        result = {
            "greeting": greeting,
            "cards": cards,
            "top_transactions": top_transactions,
            "currency_rates": currency_rates,
            "stock_prices": stock_prices
        }

        logger.info("Главная страница успешно сформирована")
        return json.dumps(result, ensure_ascii=False, indent=2)

    except Exception as e:
        logger.error(f"Ошибка при формировании главной страницы: {e}")
        error_response = {
            "error": f"Произошла ошибка: {str(e)}"
        }
        return json.dumps(error_response, ensure_ascii=False, indent=2)
