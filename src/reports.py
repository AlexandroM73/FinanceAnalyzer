import json
import logging
import pandas as pd
from datetime import datetime, timedelta
from typing import Optional, Callable
import os

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


# --- ДЕКОРАТОР ДЛЯ ЗАПИСИ ОТЧЁТА В ФАЙЛ ---
def save_report_to_file(filename: Optional[str] = None):
    def decorator(func: Callable) -> Callable:
        def wrapper(*args, **kwargs):
            # 1. Получаем результат (DataFrame)
            result_df = func(*args, **kwargs)

            # Проверка на пустой DataFrame
            if result_df.empty:
                logger.warning(f"Не сохранён отчёт {func.__name__} — пустой DataFrame")
                return result_df

            # 2. Преобразуем DataFrame в JSON-строку
            try:
                # Создаём копию для преобразования
                data_for_json = result_df.copy()

                # Преобразуем все колонки с датами в строки
                for col in data_for_json.columns:
                    if data_for_json[col].dtype == 'datetime64[ns]':

                        data_for_json[col] = data_for_json[col].dt.strftime('%Y-%m-%d')

                # Преобразуем в словарь и затем в JSON
                result_dict = data_for_json.to_dict(orient='records')
                result_json = json.dumps(result_dict, ensure_ascii=False, indent=2)

            except Exception as e:
                logger.error(f"Ошибка при преобразовании DataFrame в JSON: {e}")
                raise

            # 3. Формируем имя файла
            if filename is None:
                func_name = func.__name__
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                filename = f"{func_name}_{timestamp}.json"

            # Обработка конфликта имён файлов
            counter = 1
            original_filename = filename
            while os.path.exists(filename):
                name, ext = os.path.splitext(original_filename)
                filename = f"{name}_{counter}{ext}"
                counter += 1

            # 4. Записываем в файл
            try:
                with open(filename, 'w', encoding='utf-8') as f:
                    f.write(result_json)
                logger.info(f"Отчёт сохранён в файл: {filename}")
            except Exception as e:
                logger.error(f"Ошибка при записи файла {filename}: {e}")
                raise

            # 5. Возвращаем исходный DataFrame
            return result_df
        return wrapper
    return decorator



# --- ОТЧЁТЫ ---
@save_report_to_file()
def spending_by_category(
        transactions: pd.DataFrame,
        category: str,
        date: Optional[str] = None
) -> pd.DataFrame:
    logger.info(f"Запуск отчёта «Траты по категории» для категории '{category}'")

    # Валидация входных данных
    if transactions.empty:
        logger.warning("Получен пустой DataFrame")
        return pd.DataFrame()

    required_columns = ['Дата платежа', 'Категория', 'Сумма операции']
    missing_cols = [col for col in required_columns if col not in transactions.columns]
    if missing_cols:
        logger.error(f"Отсутствуют обязательные столбцы: {missing_cols}")
        return pd.DataFrame()

    # Создаём копию для избежания изменения оригинала
    df = transactions.copy()

    # Устанавливаем дату отсчёта
    if date is None:
        start_date = datetime.now()
    else:
        try:
            start_date = pd.to_datetime(date, format='%Y-%m-%d')  # Формат ГГГГ‑ММ‑ДД
        except ValueError:
            logger.error(f"Неверный формат даты: {date}. Ожидаемый формат ГГГГ‑ММ‑ДД")
            return pd.DataFrame()

    three_months_ago = start_date - timedelta(days=90)

    # Преобразуем колонку с датой платежа
    df['Дата платежа'] = pd.to_datetime(
        df['Дата платежа'],
        dayfirst=True,  # Универсальный вариант
        errors='coerce'
    )

    # Фильтруем транзакции
    filtered_df = df[
        (df['Дата платежа'] >= three_months_ago) &
        (df['Дата платежа'] <= start_date) &
        (df['Категория'] == category)
        ]

    # Группируем по месяцам и суммируем траты
    monthly_spending = filtered_df.groupby(
        filtered_df['Дата платежа'].dt.to_period('M')
    )['Сумма операции'].sum().reset_index()
    monthly_spending.columns = ['Месяц', 'Сумма']

    # Преобразуем Period в строку формата ГГГГ‑ММ
    monthly_spending['Месяц'] = monthly_spending['Месяц'].dt.strftime('%Y-%m')

    logger.info(f"Отчёт «Траты по категории» завершён. Строк в результате: {len(monthly_spending)}")
    return monthly_spending


def spending_by_weekday(transactions: pd.DataFrame, date: Optional[str] = None) -> pd.DataFrame:
    """
    Отчёт «Траты по дням недели».
    Возвращает средние траты в каждый из дней недели за последние 3 месяца.
    """
    logger.info("Запуск отчёта «Траты по дням недели»")

    # Валидация входных данных
    if transactions.empty:
        logger.warning("Получен пустой DataFrame")
        return pd.DataFrame()

    required_columns = ['Дата операции', 'Сумма операции']
    missing_cols = [col for col in required_columns if col not in transactions.columns]
    if missing_cols:
        logger.error(f"Отсутствуют обязательные столбцы: {missing_cols}")
        return pd.DataFrame()

    # Устанавливаем дату отсчёта
    if date is None:
        start_date = datetime.now()
    else:
        try:
            start_date = pd.to_datetime(date, format='%Y-%m-%d')  # Формат ГГГГ‑ММ‑ДД
        except ValueError:
            logger.error(f"Неверный формат даты: {date}. Ожидаемый формат ГГГГ‑ММ‑ДД")
            return pd.DataFrame()

    # Рассчитываем нижнюю границу периода (3 месяца назад)
    three_months_ago = start_date - timedelta(days=90)

    # Преобразуем и фильтруем данные
    df = transactions.copy()
    df['Дата операции'] = pd.to_datetime(df['Дата операции'], errors='coerce')

    # Фильтрация по периоду
    mask = (df['Дата операции'] >= three_months_ago) & (df['Дата операции'] <= start_date)
    filtered_df = df[mask]

    # Создаём столбец с названием дня недели (на русском)
    days_ru = ['Понедельник', 'Вторник', 'Среда', 'Четверг', 'Пятница', 'Суббота', 'Воскресенье']
    filtered_df['День недели'] = filtered_df['Дата операции'].dt.dayofweek.map(lambda x: days_ru[x])

    # Группировка по дню недели и расчёт среднего значения
    result = filtered_df.groupby('День недели')['Сумма операции'].mean().round(2).reset_index()
    result.columns = ['День недели', 'Средняя сумма']

    logger.info(f"Отчёт «Траты по дням недели» завершён. Строк в результате: {len(result)}")
    return result


@save_report_to_file("weekly_spending.json")  # Фиксированное имя файла
def spending_by_workday(transactions: pd.DataFrame, date: Optional[str] = None) -> pd.DataFrame:
    """
    Отчёт «Траты в рабочий/выходной день».
    Возвращает средние траты в рабочие и выходные дни за последние 3 месяца.


    Параметры:
        transactions (pd.DataFrame): Данные о транзакциях.
        date (str, optional): Дата отсчёта в формате 'ГГГГ-ММ-ДД'. Если None, берётся текущая дата.

    Возвращает:
        pd.DataFrame: 2 строки — 'Рабочий день' и 'Выходной день', столбец 'Средняя сумма'.
    """
    logger.info("Запуск отчёта «Траты в рабочий/выходной день»")

    # Валидация входных данных
    if transactions.empty:
        logger.warning("Получен пустой DataFrame")
        return pd.DataFrame()

    required_columns = ['Дата операции', 'Сумма операции']
    missing_cols = [col for col in required_columns if col not in transactions.columns]
    if missing_cols:
        logger.error(f"Отсутствуют обязательные столбцы: {missing_cols}")
        return pd.DataFrame()

    # Устанавливаем дату отсчёта
    if date is None:
        start_date = datetime.now()
    else:
        try:
            start_date = pd.to_datetime(date, format='%Y-%m-%d')  # Формат ГГГГ‑ММ‑ДД
        except ValueError:
            logger.error(f"Неверный формат даты: {date}. Ожидаемый формат ГГГГ‑ММ‑ДД")
            return pd.DataFrame()

    # Рассчитываем нижнюю границу периода (3 месяца назад)
    three_months_ago = start_date - timedelta(days=90)

    # Преобразуем и фильтруем данные
    df = transactions.copy()
    df['Дата операции'] = pd.to_datetime(df['Дата операции'], errors='coerce')

    # Фильтрация по периоду
    mask = (df['Дата операции'] >= three_months_ago) & (df['Дата операции'] <= start_date)
    filtered_df = df[mask]

    # Создаём признак: рабочий день (1) или выходной (0)
    # dt.dayofweek: 0=пн, 1=вт, ..., 4=пт, 5=сб, 6=вс
    filtered_df['Тип дня'] = filtered_df['Дата операции'].dt.dayofweek.apply(
        lambda x: 'Рабочий день' if x < 5 else 'Выходной день'
    )

    # Группировка и расчёт среднего
    result = filtered_df.groupby('Тип дня')['Сумма операции'].mean().round(2).reset_index()
    result.columns = ['Тип дня', 'Средняя сумма']

    # Гарантируем наличие обеих категорий, даже если данных нет
    if 'Рабочий день' not in result['Тип дня'].values:
        result = pd.concat([
            result,
            pd.DataFrame({'Тип дня': ['Рабочий день'], 'Средняя сумма': [0.0]})
        ], ignore_index=True)
    if 'Выходной день' not in result['Тип дня'].values:
        result = pd.concat([
            result,
            pd.DataFrame({'Тип дня': ['Выходной день'], 'Средняя сумма': [0.0]})
        ], ignore_index=True)

    # Сортируем для единообразия вывода
    result = result.sort_values('Тип дня').reset_index(drop=True)

    logger.info(f"Отчёт «Траты в рабочий/выходной день» завершён. Строк в результате: {len(result)}")
    return result
