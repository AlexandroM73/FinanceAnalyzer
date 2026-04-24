import unittest
from unittest.mock import patch, Mock
from parameterized import parameterized
import pandas as pd
from datetime import datetime, timedelta
import requests

from src.utils import (
    fetch_external_data,
    process_dashboard_metrics,
    get_dashboard_data,
    get_events_data
)

class TestUtils(unittest.TestCase):

    # Фикстура для тестовых данных
    @classmethod
    def setUpClass(cls):
        """Создаёт тестовые данные один раз для всех тестов"""
        cls.test_df = pd.DataFrame({
            'Дата операции': ['2023-10-15', '2023-10-20'],
            'Сумма': [100.0, 200.0],
            'Категория': ['Продукты', 'Развлечения']
        })

        cls.test_api_data = [
            {'date': '2023-10-01', 'value': 100},
            {'date': '2023-10-05', 'value': 200},
            {'date': '2023-10-10', 'value': 150}
        ]

        cls.reference_date = datetime(2023, 10, 15)

    def setUp(self):
        """Выполняется перед каждым тестом"""
        self.possible_names = ['Дата операции', 'Date', 'Transaction Date']

    # Тесты для find_column
    def test_find_column_found(self):
        """Тест нахождения колонки в DataFrame"""
        result = find_column(self.test_df, self.possible_names)
        self.assertEqual(result, 'Дата операции')

    def test_find_column_not_found(self):
        """Тест когда колонка не найдена"""
        not_found_names = ['Неизвестная колонка', 'Missing']
        result = find_column(self.test_df, not_found_names)
        self.assertIsNone(result)

    @parameterized.expand([
        (['Дата операции'], 'Дата операции'),
        (['Date', 'Дата операции'], 'Дата операции'),
        (['Missing', 'Дата операции'], 'Дата операции'),
    ])
    def test_find_column_parametrized(self, names_list, expected):
        """Параметризованный тест для разных списков имён колонок"""
        result = find_column(self.test_df, names_list)
        self.assertEqual(result, expected)

    def test_find_column_case_sensitive(self):
        """Тест чувствительности к регистру"""
        df_mixed = pd.DataFrame({'Дата Операции': [1, 2, 3]})
        result = find_column(df_mixed, ['дата операции', 'Дата операции'])
        self.assertIsNone(result)  # Не находит из‑за регистра

    # Тесты для fetch_external_data
    @patch('utils.requests.get')
    def test_fetch_external_data_success(self, mock_get):
        """Тест успешного запроса к API"""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {'data': 'test'}
        mock_get.return_value = mock_response

        result = fetch_external_data("https://test.api.com", {'param': 'value'})
        self.assertEqual(result, {'data': 'test'})

    @patch('utils.requests.get')
    def test_fetch_external_data_http_error(self, mock_get):
        """Тест ошибки HTTP-запроса"""
        mock_response = Mock()
        mock_response.raise_for_status.side_effect = requests.exceptions.HTTPError("404 Not Found")
        mock_get.return_value = mock_response

        with patch('utils.logging.getLogger') as mock_get_logger:
            mock_logger = Mock()
            mock_get_logger.return_value = mock_logger

            with self.assertRaises(requests.exceptions.RequestException):
                fetch_external_data("https://error.api.com", {})
            mock_logger.error.assert_called()

    @patch('utils.requests.get')
    def test_fetch_external_data_timeout(self, mock_get):
        """Тест таймаута запроса"""
        mock_get.side_effect = requests.exceptions.Timeout("Request timeout")

        with patch('utils.logging.getLogger') as mock_get_logger:
            mock_logger = Mock()
            mock_get_logger.return_value = mock_logger

            with self.assertRaises(requests.exceptions.RequestException):
                fetch_external_data("https://timeout.api.com", {})
            mock_logger.error.assert_called()

    # Тесты для process_dashboard_metrics
    def test_process_dashboard_metrics_valid_data(self):
        """Тест обработки валидных данных"""
        data = self.test_api_data
        metrics = process_dashboard_metrics(data, self.reference_date)

        self.assertEqual(metrics['total_records'], 3)
        # Все даты раньше reference_date, поэтому recent_activity = 0
        self.assertEqual(metrics['recent_activity'], 0)
        self.assertEqual(metrics['average_value'], 150.0)

    def test_process_dashboard_metrics_empty_data(self):
        """Тест с пустыми данными"""
        metrics = process_dashboard_metrics([], self.reference_date)
        self.assertEqual(metrics, {})

    def test_process_dashboard_metrics_missing_value_column(self):
        """Тест когда отсутствует колонка 'value'"""
        partial_data = [{'date': '2023-10-01'}, {'date': '2023-10-05'}]
        metrics = process_dashboard_metrics(partial_data, self.reference_date)

        self.assertEqual(metrics['total_records'], 2)
        self.assertEqual(metrics['average_value'], 0)
        self.assertIsNone(metrics['max_value'])
        self.assertIsNone(metrics['min_value'])


    def test_process_dashboard_metrics_with_nan_values(self):
        """Тест обработки NaN‑значений в данных"""
        data_with_nan = [
            {'date': '2023-10-01', 'value': 100},
            {'date': '2023-10-05', 'value': float('nan')},
            {'date': '2023-10-10', 'value': 150}
        ]
        metrics = process_dashboard_metrics(data_with_nan, self.reference_date)

        self.assertEqual(metrics['total_records'], 3)
        # NaN игнорируются при расчёте среднего
        self.assertEqual(metrics['average_value'], 125.0)

    @parameterized.expand([
        ([], None, {}),  # Пустые данные
        ([{'date': '2023-10-01', 'value': 50}], datetime(2023, 10, 5), {'total_records': 1, 'recent_activity': 1, 'average_value': 50.0}),
        ([{'date': '2023-09-01', 'value': 100}], datetime(2023, 10, 5), {'total_records': 1, 'recent_activity': 0, 'average_value': 100.0}),
    ])
    def test_process_dashboard_metrics_parametrized(self, data, reference_date, expected_metrics):
        """Параметризованный тест для process_dashboard_metrics"""
        if data:
            # Преобразуем строки дат в datetime
            for item in data:
                if 'date' in item:
                    item['date'] = pd.to_datetime(item['date'])

        metrics = process_dashboard_metrics(data, reference_date)

        # Проверяем наличие всех ожидаемых ключей
        for key in expected_metrics.keys():
            self.assertIn(key, metrics)

        # Сравниваем значения по каждому ключу
        for key, expected_value in expected_metrics.items():
            if key in metrics:
                if isinstance(expected_value, float):
                    # Для чисел с плавающей точкой используем почти равное сравнение
                    self.assertAlmostEqual(metrics[key], expected_value, places=2)
                else:
                    self.assertEqual(metrics[key], expected_value)

    # Тесты для get_dashboard_data
    @patch('utils.fetch_external_data')
    @patch('utils.logging.getLogger')
    def test_get_dashboard_data_success(self, mock_get_logger, mock_fetch_data):
        """Тест успешного получения данных дашборда"""
        mock_logger = Mock()
        mock_get_logger.return_value = mock_logger
        mock_fetch_data.return_value = self.test_api_data

        result = get_dashboard_data(self.reference_date)

        self.assertEqual(result['status'], 'success')
        self.assertTrue('metrics' in result)
        self.assertEqual(result['reference_date'], self.reference_date.isoformat())
        mock_logger.info.assert_any_call(f"Получение данных дашборда для даты: {self.reference_date}")

    @patch('utils.fetch_external_data')
    def test_get_dashboard_data_api_error(self, mock_fetch_data):
        """Тест ошибки при запросе к API"""
        mock_fetch_data.side_effect = Exception("API Error")

        result = get_dashboard_data(self.reference_date)

        self.assertEqual(result['status'], 'error')
        self.assertTrue('error' in result)

    @parameterized.expand([
        (datetime(2023, 10, 1), 3),  # Ранняя дата — все события
        (datetime(2023, 10, 31), 0),  # Поздняя дата — нет событий
    ])
    @patch('utils.fetch_external_data')
    def test_get_dashboard_data_with_different_dates(self, ref_date, expected_recent, mock_fetch):
        """Параметризованный тест для get_dashboard_data с разными датами"""
        mock_fetch.return_value = self.test_api_data

        result = get_dashboard_data(ref_date)
        if result['status'] == 'success':
            self.assertEqual(
                result['metrics']['recent_activity'],
                expected_recent
            )

    # Тесты для get_events_data
    def test_get_events_data_valid_transactions(self):
        """Тест обработки валидных транзакций"""
        # Добавляем колонку 'Дата операции' в формате datetime
        df_with_dates = self.test_df.copy()
        df_with_dates['Дата операции'] = pd.to_datetime(df_with_dates['Дата операции'])

        result = get_events_data(df_with_dates)

        self.assertEqual(result['status'], 'success')
        self.assertEqual(result['total_count'], 2)
        self.assertEqual(len(result['events']), 2)

    def test_get_events_data_empty_dataframe(self):
        """Тест с пустым DataFrame"""
        empty_df = pd.DataFrame()
        result = get_events_data(empty_df)

        self.assertEqual(result['status'], 'success')
        self.assertEqual(result['total_count'], 0)
        self.assertEqual(len(result['events']), 0)

    @patch('utils.logging.getLogger')
    def test_get_events_data_processing_error(self, mock_get_logger):
        """Тест ошибки обработки данных событий"""
        mock_logger = Mock()
        mock_get_logger.return_value = mock_logger


        # Создаём DataFrame с некорректными данными для вызова ошибки
        faulty_df = pd.DataFrame({
            'Дата операции': ['некорректная_дата', '2023-10-20'],
            'Сумма': [100.0, 200.0]
        })

        result = get_events_data(faulty_df)

        self.assertEqual(result['status'], 'error')
        self.assertTrue('error' in result)
        mock_logger.error.assert_called()

    def test_get_events_data_recent_events_filtering(self):
        """Тест фильтрации событий за последние 30 дней"""
        # Создаём DataFrame с датами в разных периодах
        dates = [
            datetime.now() - timedelta(days=15),  # В пределах 30 дней
            datetime.now() - timedelta(days=35),  # За пределами 30 дней
            datetime.now() - timedelta(days=5)  # В пределах 30 дней
        ]

        events_df = pd.DataFrame({
            'Дата операции': dates,
            'Описание': ['Событие 1', 'Событие 2', 'Событие 3'],
            'Сумма': [100, 200, 150]
        })

        result = get_events_data(events_df)

        self.assertEqual(result['total_count'], 2)  # Только 2 события за последние 30 дней
        self.assertEqual(len(result['events']), 2)

    def test_get_events_data_limit_output(self):
        """Тест ограничения вывода событий (максимум 50 записей)"""
        # Создаём DataFrame с 60 событиями
        large_df = pd.DataFrame([
            {
                'Дата операции': datetime.now() - timedelta(days=i),
                'Описание': f'Событие {i}',
                'Сумма': i * 10
            }
            for i in range(60)
        ])

        result = get_events_data(large_df)

        self.assertEqual(result['total_count'], 60)
        self.assertEqual(len(result['events']), 50)  # Ограничение до 50 записей

    @patch('utils.logging.getLogger')
    def test_logging_consistency(self, mock_get_logger):
        """Тест согласованности логирования во всех функциях"""
        mock_logger = Mock()
        mock_get_logger.return_value = mock_logger

        # Вызываем разные функции и проверяем логирование
        find_column(self.test_df, ['Дата операции'])
        fetch_external_data("https://test.api.com", {})
        process_dashboard_metrics([], datetime.now())

        # Проверяем, что логирование вызывалось в каждой функции
        self.assertTrue(mock_logger.info.call_count >= 3)

if __name__ == '__main__':
    unittest.main()
