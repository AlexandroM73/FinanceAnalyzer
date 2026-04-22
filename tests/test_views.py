import unittest
from unittest.mock import patch, Mock
from datetime import datetime
from flask import jsonify
from src.views import app

class TestViews(unittest.TestCase):

    def setUp(self):
        """Настраивает тестовый клиент Flask перед каждым тестом"""
        self.app = app.test_client()
        self.app.testing = True

    # Тесты для маршрута /home
    @patch('src.utils.get_dashboard_data')
    def test_home_page_success(self, mock_get_dashboard_data):
        """Тест успешного запроса к /home с корректной датой"""
        mock_get_dashboard_data.return_value = {
            "timestamp": "2023-10-15T12:00:00",
            "reference_date": "2023-10-15T00:00:00",
            "metrics": {"total_records": 10},
            "status": "success"
        }

        response = self.app.get('/home?datetime=2023-10-15 12:00:00')

        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        self.assertEqual(data['status'], 'success')
        self.assertTrue('metrics' in data)

    def test_home_page_missing_datetime_param(self):
        """Тест когда параметр datetime отсутствует"""
        response = self.app.get('/home')

        self.assertEqual(response.status_code, 400)
        data = response.get_json()
        self.assertEqual(data['error'], 'Параметр datetime обязателен')

    def test_home_page_invalid_datetime_format(self):
        """Тест с некорректным форматом даты"""
        test_cases = [
            '2023/10/15 12:00:00',  # Неверный разделитель
            '15-10-2023 12:00:00',  # DD-MM-YYYY
            '2023-10-15',           # Отсутствует время
            'invalid-date'           # Совсем некорректная
        ]

        for invalid_date in test_cases:
            with self.subTest(date=invalid_date):
                response = self.app.get(f'/home?datetime={invalid_date}')
                self.assertEqual(response.status_code, 400)
                data = response.get_json()
                self.assertIn('Неверный формат даты', data['error'])

    @patch('src.utils.get_dashboard_data')
    def test_home_page_dashboard_error(self, mock_get_dashboard_data):
        """Тест ошибки во вспомогательной функции get_dashboard_data"""
        mock_get_dashboard_data.return_value = {
            "error": "API Error",
            "status": "error"
        }

        response = self.app.get('/home?datetime=2023-10-15 12:00:00')

        self.assertEqual(response.status_code, 200)  # Функция возвращает 200 даже при ошибке внутри
        data = response.get_json()
        self.assertEqual(data['status'], 'error')
        self.assertTrue('error' in data)

    # Тесты для маршрута /events
    @patch('pandas.read_excel')
    @patch('src.utils.get_events_data')
    def test_events_page_success(self, mock_get_events_data, mock_read_excel):
        """Тест успешного запроса к /events"""
        # Настраиваем моки
        mock_df = Mock()
        mock_df.columns = ['Дата операции', 'Сумма']
        mock_read_excel.return_value = mock_df

        mock_get_events_data.return_value = {
            "events": [{"id": 1, "amount": 100}],
            "total_count": 1,
            "processed_date": "2023-10-15T12:00:00",
            "status": "success"
        }

        response = self.app.get('/events')

        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        self.assertEqual(data['status'], 'success')
        self.assertEqual(len(data['events']), 1)

        # Проверяем, что read_excel был вызван с правильным путём
        mock_read_excel.assert_called_with('data/operations.xlsx')

    @patch('pandas.read_excel')
    def test_events_page_excel_read_error(self, mock_read_excel):
        """Тест ошибки при чтении Excel‑файла"""
        mock_read_excel.side_effect = Exception("Файл не найден")

        response = self.app.get('/events')

        self.assertEqual(response.status_code, 500)
        data = response.get_json()
        self.assertEqual(data['status'], 'error')
        self.assertIn('Ошибка при загрузке данных', data['error'])

    @patch('pandas.read_excel')
    @patch('src.utils.get_events_data')
    def test_events_page_processing_error(self, mock_get_events_data, mock_read_excel):
        """Тест ошибки в обработке данных событий"""
        mock_df = Mock()
        mock_df.columns = ['Дата операции']
        mock_read_excel.return_value = mock_df
        mock_get_events_data.side_effect = Exception("Processing error")

        response = self.app.get('/events')

        self.assertEqual(response.status_code, 500)
        data = response.get_json()
        self.assertEqual(data['status'], 'error')
        self.assertIn('Ошибка при загрузке данных', data['error'])

    @patch('pandas.read_excel')
    @patch('src.utils.get_events_data')
    def test_events_page_empty_dataframe(self, mock_get_events_data, mock_read_excel):
        """Тест с пустым DataFrame из Excel"""
        empty_df = pd.DataFrame()
        mock_read_excel.return_value = empty_df
        mock_get_events_data.return_value = {
            "events": [],
            "total_count": 0,
            "processed_date": "2023-10-15T12:00:00",
            "status": "success"
        }

        response = self.app.get('/events')


        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        self.assertEqual(data['total_count'], 0)
        self.assertEqual(len(data['events']), 0)

    @patch('pandas.read_excel')
    @patch('src.utils.get_events_data')
    def test_events_page_missing_date_column(self, mock_get_events_data, mock_read_excel):
        """Тест когда в Excel отсутствует колонка 'Дата операции'"""
        partial_df = pd.DataFrame({'Сумма': [100, 200]})
        mock_read_excel.return_value = partial_df
        # get_events_data должен обработать отсутствие колонки корректно
        mock_get_events_data.return_value = {
            "events": [],
            "total_count": 0,
            "processed_date": "2023-10-15T12:00:00",
            "status": "success"
        }

        response = self.app.get('/events')

        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        self.assertEqual(data['total_count'], 0)

    # Дополнительные параметризованные тесты
        @parameterized.expand([
            ('2023-01-01 00:00:00', 2023),
            ('2024-12-31 23:59:59', 2024),
            ('2025-06-15 12:30:45', 2025)
        ])
        @patch('src.utils.get_dashboard_data')
        def test_home_page_different_dates(self, date_string, expected_year, mock_get_dashboard_data):
            """Параметризованный тест для разных дат в запросе /home"""
            mock_get_dashboard_data.return_value = {
                "timestamp": datetime.now().isoformat(),
                "reference_date": date_string.replace(' ', 'T'),
                "metrics": {"year": expected_year},
                "status": "success"
            }

            response = self.app.get(f'/home?datetime={date_string}')

            self.assertEqual(response.status_code, 200)
            data = response.get_json()
            self.assertEqual(data['status'], 'success')
            # Проверяем, что год в reference_date соответствует ожидаемому
            ref_date = data['reference_date']
            self.assertIn(str(expected_year), ref_date)

        @patch('pandas.read_excel')
        @patch('src.utils.get_events_data')
        def test_events_page_large_dataset(self, mock_get_events_data, mock_read_excel):
            """Тест обработки большого набора данных"""
            # Создаём большой DataFrame для тестирования
            large_data = [
                {
                    'Дата операции': datetime.now() - timedelta(days=i),
                    'Сумма': i * 10,
                    'Описание': f'Транзакция {i}'
                }
                for i in range(1000)  # 1000 записей
            ]
            large_df = pd.DataFrame(large_data)

            mock_read_excel.return_value = large_df
            # Мок для get_events_data — возвращаем упрощённый результат
            mock_get_events_data.return_value = {
                "events": large_data[:50],  # Ограничение до 50 записей
                "total_count": 1000,
                "processed_date": datetime.now().isoformat(),
                "status": "success"
            }

            response = self.app.get('/events')

            self.assertEqual(response.status_code, 200)
            data = response.get_json()
            self.assertEqual(data['total_count'], 1000)
            self.assertEqual(len(data['events']), 50)  # Проверка ограничения вывода

        @patch('pandas.read_excel')
        @patch('src.utils.get_events_data')
        def test_events_page_date_conversion(self, mock_get_events_data, mock_read_excel):
            """Тест корректного преобразования дат из Excel"""
            test_dates = [
                '2023-10-01',
                '2023-10-15',
                '2023-11-01'
            ]

            test_df = pd.DataFrame({
                'Дата операции': test_dates,
                'Сумма': [100, 200, 150]
            })

            mock_read_excel.return_value = test_df
            mock_get_events_data.return_value = {
                "events": test_df.to_dict('records'),
                "total_count": 3,
                "processed_date": datetime.now().isoformat(),
                "status": "success"
            }

            response = self.app.get('/events')

            self.assertEqual(response.status_code, 200)
            data = response.get_json()
            # Проверяем, что все даты корректно преобразованы в datetime
            for event in data['events']:
                self.assertTrue(isinstance(pd.to_datetime(event['Дата операции']), pd.Timestamp))

        # Тесты безопасности и крайних случаев
        def test_home_page_sql_injection_attempt(self):
            """Тест попытки SQL‑инъекции в параметре datetime"""
            sql_attack_strings = [
                "2023-10-15 12:00:00'; DROP TABLE users; --",
                "2023-10-15 12:00:00 OR '1'='1",
                "2023-10-15 12:00:00; SELECT SLEEP(5)"
            ]

            for attack_string in sql_attack_strings:
                with self.subTest(attack=attack_string):
                    response = self.app.get(f'/home?datetime={attack_string}')
                    # Должен вернуть ошибку формата, а не выполнить SQL
                    self.assertEqual(response.status_code, 400)
                    data = response.get_json()
                    self.assertIn('Неверный формат даты', data['error'])

        def test_home_page_xss_attempt(self):
            """Тест попытки XSS‑атаки в параметре datetime"""
            xss_attack_strings = [
                "2023-10-15 12:00:00<script>alert('xss')</script>",
                "2023-10-15 12:00:00\"><img src=x onerror=alert(1)>",
                "2023-10-15 12:00:00' onmouseover='alert(1)'"
            ]

            for attack_string in xss_attack_strings:
                with self.subTest(attack=attack_string):
                    response = self.app.get(f'/home?datetime={attack_string}')
                    self.assertEqual(response.status_code, 400)
                    data = response.get_json()
                    self.assertIn('Неверный формат даты', data['error'])

        @patch('pandas.read_excel')
        def test_events_page_file_not_found(self, mock_read_excel):
            """Тест когда Excel‑файл отсутствует"""
            mock_read_excel.side_effect = FileNotFoundError("Файл data/operations.xlsx не найден")

            response = self.app.get('/events')

            self.assertEqual(response.status_code, 500)
            data = response.get_json()
            self.assertEqual(data['status'], 'error')
            self.assertIn('Ошибка при загрузке данных', data['error'])
            self.assertIn('Файл не найден', data['error'])

        @patch('pandas.read_excel')
        def test_events_page_corrupted_file(self, mock_read_excel):
            """Тест когда Excel‑файл повреждён"""
            mock_read_excel.side_effect = Exception("Повреждённый файл Excel")

            response = self.app.get('/events')

            self.assertEqual(response.status_code, 500)
            data = response.get_json()
            self.assertEqual(data['status'], 'error')
            self.assertIn('Повреждённый файл', data['error'])

    if __name__ == '__main__':
        unittest.main()
