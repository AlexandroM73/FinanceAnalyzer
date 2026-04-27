import unittest
from unittest.mock import patch, Mock
from parameterized import parameterized
import pandas as pd
from datetime import datetime, timedelta

from src.utils import fetch_external_data, process_dashboard_metrics, get_events_data, find_column


class TestUtils(unittest.TestCase):

    # Фикстура для тестовых данных
    @classmethod
    def setUpClass(cls):
        """Создаёт тестовые данные один раз для всех тестов"""
        cls.test_df = pd.DataFrame(
            {
                "Дата операции": ["2023-10-15", "2023-10-20"],
                "Сумма": [100.0, 200.0],
                "Категория": ["Продукты", "Развлечения"],
            }
        )

        cls.test_api_data = [
            {"date": "2023-10-01", "value": 100},
            {"date": "2023-10-05", "value": 200},
            {"date": "2023-10-10", "value": 150},
        ]

        cls.reference_date = datetime(2023, 10, 15)

    def setUp(self):
        """Выполняется перед каждым тестом"""
        self.possible_names = ["Дата операции", "Date", "Transaction Date"]

    # Тесты для find_column
    def test_find_column_found(self):
        """Тест нахождения колонки в DataFrame"""
        result = find_column(self.test_df, self.possible_names)
        self.assertEqual(result, "Дата операции")

    def test_find_column_not_found(self):
        """Тест когда колонка не найдена"""
        not_found_names = ["Неизвестная колонка", "Missing"]
        result = find_column(self.test_df, not_found_names)
        self.assertIsNone(result)

    @parameterized.expand(
        [
            (["Дата операции"], "Дата операции"),
            (["Date", "Дата операции"], "Дата операции"),
            (["Missing", "Дата операции"], "Дата операции"),
        ]
    )
    def test_find_column_parametrized(self, names_list, expected):
        """Параметризованный тест для разных списков имён колонок"""
        result = find_column(self.test_df, names_list)
        self.assertEqual(result, expected)

    def test_find_column_case_sensitive(self):
        """Тест чувствительности к регистру"""
        df_mixed = pd.DataFrame({"Дата Операции": [1, 2, 3]})
        result = find_column(df_mixed, ["дата операции", "Дата операции"])
        self.assertIsNone(result)  # Не находит из‑за регистра

    # Тесты для fetch_external_data
    @patch("requests.get")
    def test_fetch_external_data_success(self, mock_get):
        """Тест успешного запроса к API"""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"data": "test"}
        mock_get.return_value = mock_response

        result = fetch_external_data("https://test.api.com", {"param": "value"})
        self.assertEqual(result, {"data": "test"})

    # Тесты для process_dashboard_metrics

    def test_process_dashboard_metrics_empty_data(self):
        """Тест с пустыми данными"""
        metrics = process_dashboard_metrics([], self.reference_date)
        self.assertEqual(metrics, {})

    # Тесты для get_events_data

    def test_get_events_data_empty_dataframe(self):
        """Тест с пустым DataFrame"""
        empty_df = pd.DataFrame()
        result = get_events_data(empty_df)

        self.assertEqual(result["status"], "success")
        self.assertEqual(result["total_count"], 0)
        self.assertEqual(len(result["events"]), 0)

    def test_get_events_data_recent_events_filtering(self):
        """Тест фильтрации событий за последние 30 дней"""
        # Создаём DataFrame с датами в разных периодах
        dates = [
            datetime.now() - timedelta(days=15),  # В пределах 30 дней
            datetime.now() - timedelta(days=35),  # За пределами 30 дней
            datetime.now() - timedelta(days=5),  # В пределах 30 дней
        ]

        events_df = pd.DataFrame(
            {"Дата операции": dates, "Описание": ["Событие 1", "Событие 2", "Событие 3"], "Сумма": [100, 200, 150]}
        )

        result = get_events_data(events_df)

        self.assertEqual(result["total_count"], 2)  # Только 2 события за последние 30 дней
        self.assertEqual(len(result["events"]), 2)


if __name__ == "__main__":
    unittest.main()
