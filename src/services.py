import logging
import pandas as pd
from datetime import datetime
from typing import Dict, Any, Optional, List

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def find_column_in_dict(transaction: Dict[str, Any], possible_names: list) -> Optional[str]:
    """
    Ищет ключ в словаре по списку возможных имён.
    Возвращает первое найденное имя ключа или None.
    """
    for name in possible_names:
        if name in transaction:
            return transaction[name]
    return None


def log_service_start(service_name: str, **kwargs) -> None:
    """Шаблон логирования запуска сервиса."""
    params = ", ".join(f"{k}={v}" for k, v in kwargs.items())
    logger.info(f"Запуск сервиса '{service_name}' с параметрами: {params}")


def calculate_cashback_categories(year: int, month: int, transactions: pd.DataFrame) -> Dict[str, Any]:
    """
    Сервис «Выгодные категории повышенного кешбэка».
    Принимает год, месяц и DataFrame транзакций.
    Возвращает словарь с категориями и суммами для кешбэка.
    """
    log_service_start("calculate_cashback_categories", year=year, month=month)

    # Валидация входных данных
    if not (1 <= month <= 12):
        logger.error("Неверный месяц: должен быть от 1 до 12")
        return {"error": "Неверный месяц. Должен быть от 1 до 12", "status": "error"}

    # Проверяем, пустой ли DataFrame
    if transactions.empty:
        logger.warning("Получен пустой DataFrame транзакций")
        return {"year": year, "month": month, "categories": {}, "total_amount": 0.0, "status": "success"}

    df = transactions.copy()

    # Ищем корректные имена столбцов
    date_col = find_column_in_dict(df, ["Дата платежа", "Дата операции", "Payment Date", "Date"])
    category_col = find_column_in_dict(df, ["Категория", "Category"])
    amount_col = find_column_in_dict(df, ["Сумма операции", "Amount", "Сумма"])
    cashback_col = find_column_in_dict(df, ["Кэшбэк", "Cashback", "IsCashback"])

    # Проверяем наличие всех необходимых столбцов
    if not all([date_col, category_col, amount_col]):
        missing = []
        if not date_col:
            missing.append("Дата платежа")
        if not category_col:
            missing.append("Категория")
        if not amount_col:
            missing.append("Сумма операции")

        logger.error(f"Отсутствуют обязательные столбцы: {missing}")
        return {"error": f"Отсутствуют обязательные столбцы: {', '.join(missing)}", "status": "error"}

    # Преобразуем столбец с датой в datetime с гибким парсингом
    df[date_col] = pd.to_datetime(df[date_col], dayfirst=True, errors="coerce")

    # Определяем условие для транзакций с кешбэком
    if cashback_col and cashback_col in df.columns:
        # Создаём булевую маску для строк с кешбэком
        cashback_mask = df[cashback_col].astype(str).str.lower().isin(["true", "1", "да", "yes"])
    else:
        # Если колонки нет, считаем все транзакции подходящими для кешбэка
        cashback_mask = pd.Series([True] * len(df), index=df.index)

    # Фильтруем транзакции за указанный период и с кешбэком
    filtered_transactions = df[(df[date_col].dt.year == year) & (df[date_col].dt.month == month) & cashback_mask]

    # Если нет транзакций с кешбэком, возвращаем пустой результат
    if filtered_transactions.empty:
        logger.info("Транзакций с кешбэком за указанный период не найдено")
        return {"year": year, "month": month, "categories": {}, "total_amount": 0.0, "status": "success"}

    # Агрегация по категориям: суммируем сумму для каждой категории
    category_totals = filtered_transactions.groupby(category_col)[amount_col].sum().to_dict()

    # Округляем суммы до 2 знаков после запятой
    category_totals = {k: round(v, 2) for k, v in category_totals.items()}
    total_amount = round(sum(category_totals.values()), 2)

    # Формируем ответ
    result = {
        "year": year,
        "month": month,
        "categories": category_totals,
        "total_amount": total_amount,
        "status": "success",
    }

    logger.info(f"Расчёт кешбэка завершён. Найдено категорий: {len(category_totals)}")
    return result


def investment_bank(month: str, transactions: List[Dict[str, Any]], limit: int) -> float:
    """
    Сервис «Инвесткопилка».

    Принимает:
    - month: месяц в формате 'YYYY-MM'
    - transactions: список словарей с транзакциями
    - limit: лимит округления (10, 50, 100)

    Возвращает:
    - float: сумму, которую удалось бы отложить в «Инвесткопилку»
    Формат транзакции:
    {
        "Дата операции": "YYYY-MM-DD",
        "Сумма операции": float
    }
    """
    logger.info(
        f"Запуск сервиса 'investment_bank' с параметрами: month={month}, limit={limit}, "
        f"количество транзакций={len(transactions)}"
    )

    # Валидация лимита округления
    if limit not in [10, 50, 100]:
        logger.error(f"Неверный лимит округления: {limit}. Должен быть 10, 50 или 100")
        return 0.0

    # Парсинг месяца
    try:
        target_year, target_month = map(int, month.split("-"))
        if not (1 <= target_month <= 12):
            raise ValueError("Номер месяца должен быть от 1 до 12")
    except ValueError as e:
        logger.error(f"Неверный формат месяца: {month}. Ожидаемый формат 'YYYY-MM': {e}")
        return 0.0

    def calculate_rounding_difference(amount: float, limit: int) -> float:
        """
        Рассчитывает разницу для Инвесткопилки с учётом лимита округления.
        Пример: сумма 123.50, лимит 10 → округляем до 130 → откладываем 6.50
        """
        if amount <= 0:
            return 0.0
        # Округление вверх до ближайшего кратного limit
        rounded_up = ((amount // limit) + 1) * limit
        difference = rounded_up - amount
        return difference

    investment_sum = 0.0

    for i, transaction in enumerate(transactions):
        try:
            # Извлекаем дату операции
            date_str = transaction.get("Дата операции")
            if not date_str:
                logger.warning(f"Транзакция {i}: отсутствует поле 'Дата операции', пропускаем")
                continue

            # Парсим дату
            transaction_date = datetime.strptime(date_str, "%Y-%m-%d")
            if transaction_date.year != target_year or transaction_date.month != target_month:
                # Транзакция не относится к целевому месяцу
                continue

            # Извлекаем сумму операции
            amount = transaction.get("Сумма операции")
            if amount is None:
                logger.warning(f"Транзакция {i}: отсутствует поле 'Сумма операции', пропускаем")
                continue

            # Приводим сумму к числу
            try:
                amount_float = float(amount)
            except (ValueError, TypeError):
                logger.warning(f"Транзакция {i}: некорректная сумма '{amount}', пропускаем")
                continue

            # Рассчитываем разницу для Инвесткопилки
            difference = calculate_rounding_difference(amount_float, limit)
            investment_sum += difference

        except Exception as e:
            logger.warning(f"Ошибка при обработке транзакции {i}: {e}. Пропускаем транзакцию")
            continue

    # Исправленное место: используем одну переменную для округления, логирования и возврата
    investment_sum_rounded = round(investment_sum, 2)
    logger.info(f"Расчёт Инвесткопилки завершён. Сумма: {investment_sum_rounded:.2f} руб.")
    return investment_sum_rounded


# def simple_transaction_search(
#         transactions: pd.DataFrame,
#         search_term: str,
#         column_name: Optional[str] = None
# ) -> pd.DataFrame:
#     logger.info(f"Запуск поиска транзакций по запросу: '{search_term}'")
#
#     df = transactions.copy()
#
#     if column_name:
#         # Поиск в конкретной колонке
#         if column_name not in df.columns:
#             raise ValueError(f"Колонка '{column_name}' не найдена")
#         result = df[df[column_name].astype(str).str.contains(search_term, case=False, na=False)]
#     else:
#         # Поиск по всем колонкам
#         result = pd.DataFrame()
#         for col in df.columns:
#             try:
#                 mask = df[col].astype(str).str.contains(search_term, case=False, na=False)
#                 result = pd.concat([result, df[mask]], ignore_index=True)
#             except (KeyError, AttributeError, TypeError) as e:
#                 logger.warning(f"Ошибка при поиске в колонке {col}: {e}")
#                 continue
#
#     logger.info(f"Найдено {len(result)} транзакций")
#     return result


def simple_transaction_search(
    transactions: pd.DataFrame, search_term: str, column_name: Optional[str] = None
) -> pd.DataFrame:
    logger.info(f"Запуск поиска транзакций по запросу: '{search_term}'")

    # Проверка типа входных данных
    if not isinstance(transactions, pd.DataFrame):
        logger.error(f"Ожидался DataFrame, получен {type(transactions)}")
        return pd.DataFrame()

    df = transactions.copy()

    if column_name:
        # Поиск в конкретной колонке
        if column_name not in df.columns:
            raise ValueError(f"Колонка '{column_name}' не найдена")
        result = df[df[column_name].astype(str).str.contains(search_term, case=False, na=False)]
    else:
        # Поиск по всем колонкам
        result = pd.DataFrame()
        for col in df.columns:
            try:
                mask = df[col].astype(str).str.contains(search_term, case=False, na=False)
                result = pd.concat([result, df[mask]], ignore_index=True)
            except (KeyError, AttributeError, TypeError) as e:
                logger.warning(f"Ошибка при поиске в колонке {col}: {e}")
                continue

    logger.info(f"Найдено {len(result)} транзакций")
    return result


def transactions_with_phone_numbers(transactions: pd.DataFrame) -> pd.DataFrame:
    logger.info("Запуск поиска транзакций с телефонными номерами")

    df = transactions.copy()
    phone_pattern = r"\+?\d{10,15}"
    result = pd.DataFrame()

    for col in df.columns:
        try:
            mask = df[col].astype(str).str.contains(phone_pattern, na=False)
            if mask.any():
                temp_df = df[mask].copy()
                temp_df["Найденный номер"] = df[col][mask].astype(str)
                result = pd.concat([result, temp_df], ignore_index=True)
        except (KeyError, AttributeError, TypeError) as e:
            logger.warning(f"Ошибка при поиске по колонке {col}: {e}")
            continue

    logger.info(f"Найдено транзакций с номерами: {len(result)}")
    return result


def transfers_to_individuals(transactions: pd.DataFrame) -> pd.DataFrame:
    logger.info("Запуск поиска переводов физическим лицам")

    df = transactions.copy()
    keywords = ["перевод", "перевести", "физлицо", "физическому лицу"]
    result = pd.DataFrame()

    for col in df.columns:
        for keyword in keywords:
            try:
                mask = df[col].astype(str).str.contains(keyword, case=False, na=False)
                if mask.any():
                    temp_df = df[mask].copy()
                    temp_df["Ключевое слово"] = keyword
                    result = pd.concat([result, temp_df], ignore_index=True)
            except Exception as e:
                logger.warning(f"Ошибка при поиске по колонке {col}: {e}")
                continue

    logger.info(f"Найдено переводов физлицам: {len(result)}")
    return result
