import logging
import pandas as pd
import requests
from datetime import datetime, timedelta

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def find_column(dataframe, column_names):
    """
    Ищет первый существующий столбец из списка column_names в DataFrame.
    Возвращает имя столбца или None, если ни один не найден.
    """
    for col in column_names:
        if col in dataframe.columns:
            return col
    return None


def fetch_external_data(api_url: str, params: dict) -> dict:
    """
    Вспомогательная функция для получения данных через API.
    Использует библиотеку requests для HTTP‑запросов.
    """
    try:
        response = requests.get(api_url, params=params, timeout=10)
        response.raise_for_status()
        logger.info(f"Успешный запрос к API: {api_url}")
        return response.json()
    except requests.exceptions.RequestException as e:
        logger.error(f"Ошибка при запросе к API {api_url}: {e}")
        raise


def process_dashboard_metrics(data: dict, reference_date: datetime) -> dict:
    """
    Вспомогательная функция для обработки метрик дашборда.
    Использует pandas для агрегации данных и datetime для расчётов.
    """
    if not data:
        return {}

    # Пример обработки данных (можно адаптировать под реальные данные)
    df = pd.DataFrame(data)

    # Добавляем расчётные поля
    df["days_since_reference"] = (df["date"] - reference_date).dt.days

    metrics = {
        "total_records": len(df),
        "recent_activity": len(df[df["days_since_reference"] <= 7]),
        "average_value": round(df["value"].mean(), 2) if "value" in df.columns else 0,
        "max_value": df["value"].max() if "value" in df.columns else None,
        "min_value": df["value"].min() if "value" in df.columns else None,
    }

    return metrics


def get_dashboard_data(reference_date: datetime) -> dict:
    """
    Основная вспомогательная функция для страницы «Главная».
    Объединяет данные из API и локальных источников.
    """
    logger.info(f"Получение данных дашборда для даты: {reference_date}")

    try:
        # Получаем данные из внешнего API
        api_url = "https://api.example.com/dashboard"
        api_params = {"date": reference_date.strftime("%Y-%m-%d"), "limit": 100}
        external_data = fetch_external_data(api_url, api_params)

        # Обрабатываем метрики
        metrics = process_dashboard_metrics(external_data, reference_date)

        # Формируем итоговый JSON‑ответ
        result = {
            "timestamp": datetime.now().isoformat(),
            "reference_date": reference_date.isoformat(),
            "metrics": metrics,
            "status": "success",
        }

        logger.info("Данные дашборда успешно подготовлены")
        return result

    except Exception as e:
        logger.error(f"Ошибка при получении данных дашборда: {e}")
        return {"error": str(e), "status": "error"}


def get_events_data(transactions_df: pd.DataFrame) -> dict:
    """
    Вспомогательная функция для страницы «События».
    Обрабатывает DataFrame с транзакциями и возвращает JSON‑ответ.
    """
    logger.info("Обработка данных событий")

    try:
        if transactions_df.empty:
            return {"events": [], "total_count": 0, "status": "success"}

        # Пример обработки транзакций
        recent_events = transactions_df[transactions_df["Дата операции"] >= datetime.now() - timedelta(days=30)]

        events_list = recent_events.to_dict("records")

        result = {
            "events": events_list[:50],  # Ограничиваем вывод
            "total_count": len(recent_events),
            "processed_date": datetime.now().isoformat(),
            "status": "success",
        }

        logger.info(f"Обработано событий: {len(recent_events)}")
        return result

    except Exception as e:
        logger.error(f"Ошибка при обработке данных событий: {e}")
        return {"error": str(e), "status": "error"}
