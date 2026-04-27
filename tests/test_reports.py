import unittest
from unittest.mock import patch
from parameterized import parameterized
import pandas as pd

from src.reports import spending_by_category, spending_by_weekday, spending_by_workday, save_report_to_file


class TestReports(unittest.TestCase):

    # Фикстура для тестовых данных
    @classmethod
    def setUpClass(cls):
        """Создаёт тестовые данные один раз для всех тестов"""
        cls.test_transactions_df = pd.DataFrame(
            [
                {"Дата платежа": "2023-10-15", "Категория": "Продукты", "Сумма операции": 123.50},
                {"Дата платежа": "2023-10-20", "Категория": "Развлечения", "Сумма операции": 87.25},
                {"Дата платежа": "2023-09-05", "Категория": "Транспорт", "Сумма операции": 250.75},
                {"Дата платежа": "2023-08-25", "Категория": "Продукты", "Сумма операции": 99.99},
                {"Дата платежа": "2023-07-10", "Категория": "Продукты", "Сумма операции": 150.00},
            ]
        )

        cls.test_transactions_with_dates = pd.DataFrame(
            [
                {"Дата операции": "2023-10-15", "Сумма операции": 200.00},  # Воскресенье
                {"Дата операции": "2023-10-16", "Сумма операции": 150.00},  # Понедельник
                {"Дата операции": "2023-10-17", "Сумма операции": 300.00},  # Вторник
                {"Дата операции": "2023-10-21", "Сумма операции": 400.00},  # Суббота
                {"Дата операции": "2023-10-22", "Сумма операции": 500.00},  # Воскресенье
            ]
        )

    def setUp(self):
        """Выполняется перед каждым тестом"""
        self.category = "Продукты"
        self.date = "2023-10-31"

    # Тесты для spending_by_category
    @parameterized.expand(
        [("Продукты", "2023-10-31", 2), ("Развлечения", "2023-10-31", 1), ("Транспорт", "2023-10-31", 1)]
    )
    def test_spending_by_category_valid_data(self, category, date, expected_rows):
        """Параметризованный тест для корректных данных"""
        result = spending_by_category(self.test_transactions_df, category, date)
        self.assertEqual(len(result), expected_rows)
        self.assertIn("Месяц", result.columns)
        self.assertIn("Сумма", result.columns)

    def test_spending_by_category_empty_dataframe(self):
        """Тест с пустым DataFrame"""
        empty_df = pd.DataFrame()
        result = spending_by_category(empty_df, self.category, self.date)
        self.assertTrue(result.empty)

    def test_spending_by_category_missing_columns(self):
        """Тест с отсутствующими обязательными колонками"""
        partial_df = self.test_transactions_df.drop("Категория", axis=1)
        result = spending_by_category(partial_df, self.category, self.date)
        self.assertTrue(result.empty)

    @patch("src.reports.save_report_to_file")
    def test_spending_by_category_with_decorator(self, mock_decorator):
        """Тест работы с декоратором сохранения отчёта"""
        mock_decorator.return_value = lambda func: func
        result = spending_by_category(self.test_transactions_df, self.category, self.date)
        self.assertFalse(result.empty)

    # Тесты для spending_by_weekday
    def test_spending_by_weekday_valid_data(self):
        """Тест корректных данных для трат по дням недели"""
        result = spending_by_weekday(self.test_transactions_with_dates, self.date)
        # Ожидаем только дни, которые есть в данных (не обязательно все 7)
        self.assertGreaterEqual(len(result), 1)
        self.assertLessEqual(len(result), 7)
        self.assertIn("День недели", result.columns)
        self.assertIn("Средняя сумма", result.columns)

    def test_spending_by_weekday_empty_dataframe(self):
        """Тест с пустым DataFrame"""
        empty_df = pd.DataFrame()
        result = spending_by_weekday(empty_df, self.date)
        self.assertTrue(result.empty)

    def test_spending_by_weekday_missing_columns(self):
        """Тест с отсутствующими колонками"""
        partial_df = self.test_transactions_with_dates.drop("Сумма операции", axis=1)
        result = spending_by_weekday(partial_df, self.date)
        self.assertTrue(result.empty)

    # Тесты для spending_by_workday
    def test_spending_by_workday_valid_data(self):
        """Тест корректных данных для трат в рабочие/выходные дни"""
        result = spending_by_workday(self.test_transactions_with_dates, self.date)
        self.assertEqual(len(result), 2)  # Рабочий и выходной день
        self.assertIn("Тип дня", result.columns)
        self.assertIn("Средняя сумма", result.columns)
        types = result["Тип дня"].tolist()
        self.assertIn("Рабочий день", types)
        self.assertIn("Выходной день", types)

    def test_spending_by_workday_only_weekdays(self):
        """Тест когда есть только рабочие дни"""
        weekdays_only = self.test_transactions_with_dates[
            ~self.test_transactions_with_dates["Дата операции"].isin(["2023-10-21", "2023-10-22"])
        ]
        result = spending_by_workday(weekdays_only, self.date)
        types = result["Тип дня"].tolist()
        self.assertIn("Рабочий день", types)
        self.assertIn("Выходной день", types)  # Должен быть с суммой 0.0

    def test_spending_by_workday_only_weekends(self):
        """Тест когда есть только выходные дни"""
        weekends_only = self.test_transactions_with_dates[
            self.test_transactions_with_dates["Дата операции"].isin(["2023-10-21", "2023-10-22"])
        ]
        result = spending_by_workday(weekends_only, self.date)
        types = result["Тип дня"].tolist()
        self.assertIn("Рабочий день", types)  # Должен быть с суммой 0.0
        self.assertIn("Выходной день", types)

        # Проверяем, что рабочий день имеет сумму 0.0
        workday_row = result[result["Тип дня"] == "Рабочий день"]
        self.assertEqual(workday_row["Средняя сумма"].iloc[0], 0.0)

    def test_spending_by_workday_empty_dataframe(self):
        """Тест с пустым DataFrame"""
        empty_df = pd.DataFrame()
        result = spending_by_workday(empty_df, self.date)
        self.assertTrue(result.empty)

    def test_spending_by_workday_missing_columns(self):
        """Тест с отсутствующими обязательными колонками"""
        partial_df = self.test_transactions_with_dates.drop("Сумма операции", axis=1)
        result = spending_by_workday(partial_df, self.date)
        self.assertTrue(result.empty)

    # Тесты для декоратора save_report_to_file

    @patch("os.path.exists")
    @patch("builtins.open")
    def test_save_report_decorator_filename_conflict(self, mock_open, mock_path_exists):
        """Тест обработки конфликта имён файлов"""
        # Первый вызов — файл существует, второй — нет
        mock_path_exists.side_effect = [True, False]

        @save_report_to_file("existing_file.json")
        def test_func():
            return pd.DataFrame({"data": [1]})

        test_func()

        # Должен попытаться сохранить как existing_file_1.json
        mock_open.assert_called_with("existing_file_1.json", "w", encoding="utf-8")

    @patch("os.path.exists")
    @patch("builtins.open")
    def test_save_report_decorator_auto_filename(self, mock_open, mock_path_exists):
        """Тест автоматического формирования имени файла"""
        mock_path_exists.return_value = False

        @save_report_to_file()
        def another_test_func():
            return pd.DataFrame({"test": [1]})

        another_test_func()

        # Проверяем, что имя файла содержит имя функции и timestamp
        called_filename = mock_open.call_args[0][0]
        self.assertIn("another_test_func", called_filename)
        self.assertIn(".json", called_filename)
