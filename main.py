import json
import logging
from datetime import datetime
from typing import Any, Dict, List

import pandas as pd

from src.main_page import main_page
from src.reports import spending_by_category, spending_by_weekday, spending_by_workday
from src.services import (
    calculate_cashback_categories,
    investment_bank,
    simple_transaction_search,
    transactions_with_phone_numbers,
    transfers_to_individuals,
)

# Очищаем существующие обработчики, чтобы избежать конфликтов
logging.getLogger().handlers.clear()

logging.basicConfig(
    level=logging.DEBUG,  # Самый низкий уровень — записываем всё
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler("app.log", encoding="utf-8", mode="w")  # 'w' — перезаписываем файл при каждом запуске
    ],
)
logger = logging.getLogger(__name__)  # Определяем logger ДО любых вызовов


def load_transactions_from_excel() -> pd.DataFrame:
    """Загружает транзакции из Excel‑файла с обработкой ошибок."""
    try:
        df = pd.read_excel("data/operations.xlsx")
        # Проверяем наличие обязательных столбцов
        required_columns = ["Дата операции", "Категория", "Сумма операции", "Кэшбэк"]
        missing = [col for col in required_columns if col not in df.columns]
        if missing:
            raise ValueError(f"Отсутствуют столбцы: {', '.join(missing)}")
        # Преобразуем дату
        if "Дата операции" in df.columns:
            df["Дата операции"] = pd.to_datetime(df["Дата операции"], errors="coerce")
        logger.info("Данные успешно загружены из Excel")
        return df
    except FileNotFoundError:
        logger.error("Файл data/operations.xlsx не найден")
        raise
    except Exception as e:
        logger.error(f"Ошибка при загрузке данных из Excel: {e}")
        raise


def load_sample_data() -> tuple:
    """Загружает тестовые данные для демонстрации."""
    # Пример транзакций с обязательным столбцом «Кэшбэк»
    sample_transactions = [
        {
            "Дата операции": "2023-10-15 14:30:00",
            "Категория": "Продукты",
            "Сумма операции": 1500.50,
            "Кэшбэк": True,
            "Описание": "Покупка в супермаркете 'Пятёрочка'",
        },
        {
            "Дата операции": "2023-10-20 18:45:00",
            "Категория": "Развлечения",
            "Сумма операции": 800.00,
            "Кэшбэк": False,
            "Описание": "Билет в кино + попкорн",
        },
        {
            "Дата операции": "2023-11-05 12:15:00",
            "Категория": "Транспорт",
            "Сумма операции": 250.75,
            "Кэшбэк": True,
            "Описание": "Оплата такси +79161234567",
        },
    ]

    # DataFrame для отчётов
    df = pd.DataFrame(
        [
            {"Дата операции": "2023-09-01", "Категория": "Продукты", "Сумма операции": 1200.0, "Кэшбэк": True},
            {"Дата операции": "2023-09-15", "Категория": "Развлечения", "Сумма операции": 800.0, "Кэшбэк": False},
            {"Дата операции": "2023-10-01", "Категория": "Транспорт", "Сумма операции": 250.0, "Кэшбэк": True},
            {"Дата операции": "2023-10-20", "Категория": "Продукты", "Сумма операции": 900.0, "Кэшбэк": True},
        ]
    )
    df["Дата операции"] = pd.to_datetime(df["Дата операции"])

    return sample_transactions, df


def display_menu() -> int:
    """Отображает главное меню с иерархической структурой и возвращает выбор пользователя."""
    print("\n" + "=" * 60)
    print("ГЛАВНОЕ МЕНЮ ФИНАНСОВЫХ СЕРВИСОВ")
    print("=" * 60)
    print("1. Веб‑страницы:")
    print("   1.1 Главная")
    print("   1.2 События")
    print("2. Сервисы:")
    print("   2.1 Выгодные категории повышенного кешбэка")
    print("   2.2 Инвесткопилка")
    print("   2.3 Простой поиск транзакций")
    print("   2.4 Поиск транзакций с телефонными номерами")
    print("   2.5 Поиск переводов физическим лицам")
    print("3. Отчёты:")
    print("   3.1 Траты по категории")
    print("   3.2 Траты по дням недели")
    print("   3.3 Траты в рабочий/выходной день")
    print("0. Выход")
    print("-" * 60)

    while True:
        try:
            choice = input("Выберите опцию (0, 1.1–1.2, 2.1–2.5, 3.1–3.3): ").strip()

            # Обрабатываем выход
            if choice == "0":
                return 0

            # Разбираем составной выбор
            parts = choice.split(".")
            if len(parts) != 2:
                print("Ошибка: введите номер в формате X.Y (например, 2.1).")
                continue

            main_choice = int(parts[0])
            sub_choice = int(parts[1])

            # Валидация основного выбора
            if main_choice == 1:  # Веб‑страницы
                if sub_choice in [1, 2]:
                    return int(f"{main_choice}{sub_choice}")  # 11 или 12
                else:
                    print("Ошибка: для веб‑страниц доступны только 1.1 и 1.2.")
            elif main_choice == 2:  # Сервисы
                if 1 <= sub_choice <= 5:
                    return int(f"2{sub_choice}")  # 21–25
                else:
                    print("Ошибка: неверный номер сервиса. Выберите от 2.1 до 2.5.")
            elif main_choice == 3:  # Отчёты
                if 1 <= sub_choice <= 3:
                    return int(f"3{sub_choice}")  # 31–33
                else:
                    print("Ошибка: неверный номер отчёта. Выберите от 3.1 до 3.3.")
            else:
                print("Ошибка: неверный основной раздел. Выберите 1, 2 или 3.")
        except ValueError:
            print("Ошибка: пожалуйста, введите корректный номер в формате X.Y.")


def get_user_input(prompt: str, input_type: type = str) -> Any:
    """Получает ввод от пользователя с обработкой ошибок."""
    while True:
        try:
            user_input = input(prompt)
            if input_type == int:
                return int(user_input)
            elif input_type == float:
                return float(user_input)
            else:
                return user_input
        except ValueError:
            print(f"Ошибка: введите корректное значение типа {input_type.__name__}.")


def display_result(result: Any, title: str = "РЕЗУЛЬТАТ"):
    """Унифицированный вывод результатов."""
    print(f"\n{title}:")
    if isinstance(result, pd.DataFrame):
        if not result.empty:
            print(result.to_string(index=False))
        else:
            print("По вашему запросу данных не найдено.")
    elif isinstance(result, dict):
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        print(result)


def run_cashback_service(transactions_df: pd.DataFrame):
    """Запуск сервиса кешбэка."""
    year = get_user_input("Год (например, 2023): ", int)
    month = get_user_input("Месяц (1–12): ", int)
    result = calculate_cashback_categories(year, month, transactions_df)
    display_result(result)


def run_investment_service(transactions_df: pd.DataFrame):
    """Запуск сервиса Инвесткопилки."""
    year = get_user_input("Год (например, 2023): ", int)
    month_num = get_user_input("Номер месяца (1–12): ", int)
    # Форматируем месяц в виде 'YYYY-MM'
    month_str = f"{year}-{month_num:02d}"

    while True:
        rounding_limit = get_user_input("Лимит округления (10, 50, 100): ", int)
        if rounding_limit in [10, 50, 100]:
            break
        print("Ошибка: лимит должен быть 10, 50 или 100.")

    # Преобразуем DataFrame в список словарей для сервиса
    transactions_list = transactions_df.to_dict("records")
    result = investment_bank(month_str, transactions_list, rounding_limit)
    display_result(result, "РЕЗУЛЬТАТ ИНВЕСТКОПИЛКИ")


def run_simple_search(transactions_df: pd.DataFrame):
    """Запуск простого поиска."""
    query = get_user_input("Введите поисковый запрос: ")
    # Передаём DataFrame, а не список словарей
    result = simple_transaction_search(query, transactions_df)
    display_result(result)


def run_phone_search(transactions: List[Dict[str, Any]]):
    """Запуск поиска по телефонным номерам."""
    result = transactions_with_phone_numbers(transactions)
    display_result(result)


# def simple_transaction_search(query: str, data: pd.DataFrame) -> pd.DataFrame:
#     if data.empty:
#         return pd.DataFrame()
#     # Ищем во всех строковых колонках
#     mask = data.astype(str).apply(lambda row: row.str.contains(query, case=False, na=False)).any(axis=1)
#     return data[mask]


# def run_category_report(transactions_df: pd.DataFrame):
#     """Запуск отчёта «Траты по категории»."""
#     category = get_user_input("Категория (например, 'Продукты'): ")
#
#     while True:
#         date_str = get_user_input("Дата отсчёта (ГГГГ‑ММ‑ДД): ")
#         try:
#             reference_date = datetime.strptime(date_str, "%Y-%m-%d")
#             break
#         except ValueError:
#             print("Ошибка: неверный формат даты. Введите в формате ГГГГ‑ММ‑ДД (например, 2023‑10‑15).")
#
#     try:
#         # Фильтруем DataFrame по дате (сравниваем datetime с Timestamp)
#         filtered_df = transactions_df[
#             transactions_df['Дата операции'].dt.date == reference_date.date()
#         ]
#         result = spending_by_category(filtered_df, category, date_str)
#         display_result(result, "ОТЧЁТ «ТРАТЫ ПО КАТЕГОРИИ»")
#     except Exception as e:
#         logger.error(f"Ошибка при формировании отчёта: {e}")
#         print(f"Ошибка при формировании отчёта: {e}")
def run_category_report(transactions_df: pd.DataFrame):
    """Запуск отчёта «Траты по категории»."""
    category = get_user_input("Категория (например, 'Продукты'): ")

    # Получаем дату отсчёта с валидацией формата
    while True:
        date_str = get_user_input("Дата отсчёта (ГГГГ‑ММ‑ДД, или оставьте пустым для текущей даты): ")
        if not date_str.strip():  # Если пользователь оставил поле пустым
            reference_date = None  # Используем текущую дату в функции отчёта
            break
        try:
            # Проверяем корректность формата даты
            datetime.strptime(date_str, "%Y-%m-%d")
            reference_date = date_str
            break
        except ValueError:
            print(
                "Ошибка: неверный формат даты. Введите в формате ГГГГ‑ММ‑ДД (например, 2023‑10‑15) или оставьте поле пустым."
            )

    try:
        # Передаём весь DataFrame и параметры в функцию отчёта
        # Функция spending_by_category сама выполнит фильтрацию за последние 3 месяца
        result = spending_by_category(transactions_df, category, reference_date)

        # Отображаем результат
        display_result(result, "ОТЧЁТ «ТРАТЫ ПО КАТЕГОРИИ»")

    except Exception as e:
        logger.error(f"Ошибка при формировании отчёта: {e}")
        print(f"Произошла ошибка при формировании отчёта: {e}")


def run_weekday_report(transactions_df: pd.DataFrame):
    """Запуск отчёта «Траты по дням недели»."""
    date_input = get_user_input("Введите дату для отчёта (ГГГГ‑ММ‑ДД, или оставьте пустым для текущей даты): ")
    reference_date = None

    if date_input.strip():
        try:
            reference_date = datetime.strptime(date_input, "%Y-%m-%d")
        except ValueError:
            print("Неверный формат даты, используется текущая дата.")

    try:
        result = spending_by_weekday(transactions_df, reference_date)
        display_result(result, "ОТЧЁТ «ТРАТЫ ПО ДНЯМ НЕДЕЛИ»")
    except Exception as e:
        logger.error(f"Ошибка при формировании отчёта «Траты по дням недели»: {e}")
        print(f"Произошла ошибка при формировании отчёта: {e}")


def run_workday_weekend_report(transactions_df: pd.DataFrame):
    """Запуск отчёта «Траты в рабочий/выходной день»."""
    date_input = get_user_input("Введите дату для отчёта (ГГГГ‑ММ‑ДД, или оставьте пустым для текущей даты): ")
    reference_date = None

    if date_input.strip():
        try:
            reference_date = datetime.strptime(date_input, "%Y-%m-%d")
        except ValueError:
            print("Неверный формат даты, используется текущая дата.")

    try:
        result = spending_by_workday(transactions_df, reference_date)
        display_result(result, "ОТЧЁТ «ТРАТЫ В РАБОЧИЙ/ВЫХОДНОЙ ДЕНЬ»")
    except Exception as e:
        logger.error(f"Ошибка при формировании отчёта «Траты в рабочий/выходной день»: {e}")
        print(f"Произошла ошибка при формировании отчёта: {e}")


def main():
    logger.info("Запуск приложения с интерактивным меню")

    # Загружаем данные один раз при старте приложения
    try:
        # Сначала пытаемся загрузить из Excel
        try:
            transactions_df = load_transactions_from_excel()
            logger.info("Использованы данные из Excel‑файла")
        except Exception as excel_error:
            logger.warning(f"Не удалось загрузить данные из Excel: {excel_error}. Используются тестовые данные.")
            # Загружаем тестовые данные
            _, transactions_df = load_sample_data()

        if not isinstance(transactions_df, pd.DataFrame):
            raise TypeError("Ошибка загрузки: данные не в формате DataFrame")
        if transactions_df.empty:
            raise ValueError("Загруженный DataFrame пуст")

    except Exception as e:
        logger.critical(f"Критическая ошибка при загрузке данных: {e}")
        print(f"Не удалось загрузить данные: {e}. Работа приложения прервана.")
        return

    while True:
        choice = display_menu()
        if choice == 0:
            print("До свидания!")
            break

        try:
            if choice == 11:  # Главная страница
                current_datetime = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                result = main_page(current_datetime)
                print(result)
            elif choice == 12:
                print("\nОткрываются события...")
                # Здесь будет вызов функции для событий

            # Сервисы
            elif choice == 21:  # Выгодные категории повышенного кешбэка
                run_cashback_service(transactions_df)
            elif choice == 22:  # Инвесткопилка
                run_investment_service(transactions_df)
            elif choice == 23:  # Простой поиск транзакций
                run_simple_search(transactions_df)
            elif choice == 24:  # Поиск транзакций с телефонными номерами
                result = transactions_with_phone_numbers(transactions_df)
                display_result(result, "РЕЗУЛЬТАТ ПОИСКА ПО ТЕЛЕФОННЫМ НОМЕРАМ")
            elif choice == 25:  # Поиск переводов физическим лицам
                result = transfers_to_individuals(transactions_df)
                display_result(result, "РЕЗУЛЬТАТ ПОИСКА ПЕРЕВОДОВ ФИЗЛИЦАМ")

            # Отчёты
            elif choice == 31:  # Траты по категории
                run_category_report(transactions_df)
            elif choice == 32:  # Траты по дням недели
                run_weekday_report(transactions_df)
            elif choice == 33:  # Траты в рабочий/выходной день
                run_workday_weekend_report(transactions_df)

        except Exception as e:
            logger.error(f"Произошла ошибка при выполнении опции {choice}: {e}")
            print(f"\nПроизошла ошибка: {e}. Попробуйте снова.")
            continue


if __name__ == "__main__":
    main()
