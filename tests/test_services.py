import unittest

import pandas as pd

from src.services import (
    calculate_cashback_categories,
    investment_bank,
    simple_transaction_search,
    transactions_with_phone_numbers,
    transfers_to_individuals,
    find_column_in_dict,
)


class TestServices(unittest.TestCase):

    # Фикстура для тестовых данных
    @classmethod
    def setUpClass(cls):
        """Создаёт тестовые данные один раз для всех тестов"""
        cls.test_transactions_df = pd.DataFrame(
            [
                {"Дата платежа": "2023-10-15", "Категория": "Продукты", "Сумма операции": 123.50, "Кэшбэк": True},
                {"Дата платежа": "2023-10-20", "Категория": "Развлечения", "Сумма операции": 87.25, "Кэшбэк": True},
                {"Дата платежа": "2023-11-05", "Категория": "Транспорт", "Сумма операции": 250.75, "Кэшбэк": False},
                {"Дата платежа": "2023-10-25", "Категория": "Продукты", "Сумма операции": 99.99, "Кэшбэк": True},
            ]
        )

        cls.test_transactions_list = [
            {"Дата операции": "2023-10-15", "Сумма операции": 123.50},
            {"Дата операции": "2023-10-20", "Сумма операции": 87.25},
            {"Дата операции": "2023-11-05", "Сумма операции": 250.75},
            {"Дата операции": "2023-10-25", "Сумма операции": 99.99},
        ]

    def setUp(self):
        """Выполняется перед каждым тестом"""
        self.year = 2023
        self.month = 10

    # Тесты для find_column_in_dict
    def test_find_column_in_dict_found(self):
        """Тест нахождения ключа в словаре"""
        transaction = {"Дата платежа": "2023-10-15", "Сумма": 100.0}
        result = find_column_in_dict(transaction, ["Дата платежа", "Date"])
        self.assertEqual(result, "2023-10-15")

    def test_find_column_in_dict_not_found(self):
        """Тест когда ключ не найден"""
        transaction = {"Дата": "2023-10-15"}
        result = find_column_in_dict(transaction, ["Дата платежа", "Payment Date"])
        self.assertIsNone(result)

    def test_calculate_cashback_empty_dataframe(self):
        """Тест с пустым DataFrame"""
        empty_df = pd.DataFrame()
        result = calculate_cashback_categories(2023, 10, empty_df)
        self.assertEqual(result["status"], "success")
        self.assertEqual(result["total_amount"], 0.0)

    def test_investment_bank_empty_transactions(self):
        """Тест с пустым списком транзакций"""
        result = investment_bank("2023-10", [], 10)
        self.assertEqual(result, 0.0)

    # Тесты для simple_transaction_search
    def test_simple_transaction_search_specific_column(self):
        """Поиск в конкретной колонке"""
        result = simple_transaction_search(self.test_transactions_df, "Продукты", "Категория")
        self.assertEqual(len(result), 2)
        self.assertTrue(all(result["Категория"] == "Продукты"))

    def test_simple_transaction_search_all_columns(self):
        """Поиск по всем колонкам"""
        result = simple_transaction_search(self.test_transactions_df, "2023-10")
        self.assertEqual(len(result), 3)  # 3 транзакции в октябре

    def test_simple_transaction_search_not_found(self):
        """Поиск, когда ничего не найдено"""
        result = simple_transaction_search(self.test_transactions_df, "Не существующая категория")
        self.assertEqual(len(result), 0)

    def test_simple_transaction_search_case_insensitive(self):
        """Поиск без учёта регистра"""
        result = simple_transaction_search(self.test_transactions_df, "продукты", "Категория")  # в нижнем регистре
        self.assertEqual(len(result), 2)
        self.assertTrue(all(result["Категория"] == "Продукты"))

        # Тесты для transactions_with_phone_numbers

    def test_transactions_with_phone_numbers_found(self):
        """Тест нахождения транзакций с номерами телефонов"""
        # Создаём DataFrame с номерами телефонов
        df_with_phones = self.test_transactions_df.copy()
        df_with_phones["Комментарий"] = [
            "Перевод +79161234567",
            "Оплата +79267654321",
            "Без номера",
            "Перевод +79031112233",
        ]

        result = transactions_with_phone_numbers(df_with_phones)
        self.assertEqual(len(result), 3)  # 3 транзакции с номерами
        # Проверяем, что все результаты содержат номера телефонов
        phone_pattern = r"\+7\d{10}"
        for comment in result["Комментарий"]:
            self.assertRegex(comment, phone_pattern)

    def test_transactions_with_phone_numbers_not_found(self):
        """Тест когда номера телефонов не найдены"""
        # DataFrame без номеров телефонов
        df_no_phones = self.test_transactions_df.copy()
        df_no_phones["Комментарий"] = ["Без номера", "Без номера", "Без номера", "Без номера"]

        result = transactions_with_phone_numbers(df_no_phones)
        self.assertEqual(len(result), 0)

    def test_transactions_with_phone_numbers_empty_dataframe(self):
        """Тест с пустым DataFrame"""
        empty_df = pd.DataFrame()
        result = transactions_with_phone_numbers(empty_df)
        self.assertEqual(len(result), 0)

        # Тесты для transfers_to_individuals

    def test_transfers_to_individuals_not_found(self):
        """Тест когда переводы физлицам не найдены"""
        # DataFrame без переводов физлицам
        df_no_transfers = self.test_transactions_df.copy()
        df_no_transfers["Тип операции"] = ["Оплата", "Оплата", "Оплата", "Оплата"]
        df_no_transfers["Получатель"] = ["Банк", "Магазин", "Сервис", "Компания"]

        result = transfers_to_individuals(df_no_transfers)
        self.assertEqual(len(result), 0)

    def test_transfers_to_individuals_empty_dataframe(self):
        """Тест с пустым DataFrame"""
        empty_df = pd.DataFrame()
        result = transfers_to_individuals(empty_df)
        self.assertEqual(len(result), 0)

        # Дополнительные тесты для edge cases


if __name__ == "__main__":
    unittest.main()
