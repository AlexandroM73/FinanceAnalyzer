import unittest
from unittest.mock import patch, Mock
from parameterized import parameterized
import pandas as pd
from datetime import datetime, timedelta
from src.reports import (
    spending_by_category,
    spending_by_weekday,
    spending_by_workday
)

class TestReports(unittest.TestCase):

    # Фикстура для тестовых данных
    @classmethod
    def setUpClass(cls):
        """Создаёт тестовые данные один раз для всех тестов"""
        cls.test_transactions_df = pd.DataFrame([
            {
                'Дата платежа': '2023-10-15',
                'Категория': 'Продукты',
                'Сумма операции': 123.50
            },
            {
                'Дата платежа': '2023-10-20',
                'Категория': 'Развлечения',
                'Сумма операции': 87.25
            },
            {
                'Дата платежа': '2023-09-05',
                'Категория': 'Транспорт',
                'Сумма операции': 250.75
            },
            {
                'Дата платежа': '2023-08-25',
                'Категория': 'Продукты',
                'Сумма операции': 99.99
            },
            {
                'Дата платежа': '2023-07-10',
                'Категория': 'Продукты',
                'Сумма операции': 150.00
            }
        ])

        cls.test_transactions_with_dates = pd.DataFrame([
            {
                'Дата операции': '2023-10-15',
                'Сумма операции': 200.00
            },
            {
                'Дата операции': '2023-10-16',  # Понедельник
                'Сумма операции': 150.00
            },
            {
                'Дата операции': '2023-10-17',  # Вторник
                'Сумма операции': 300.00
            },
            {
                'Дата операции': '2023-10-21',  # Суббота
                'Сумма операции': 400.00
            },
            {
                'Дата операции': '2023-10-22',  # Воскресенье
                'Сумма операции': 500.00
            }
        ])

    def setUp(self):
        """Выполняется перед каждым тестом"""
        self.category = 'Продукты'
        self.date = '2023-10-31'

    # Тесты для spending_by_category
    @parameterized.expand([
        ('Продукты', '2023-10-31', 2),
        ('Развлечения', '2023-10-31', 1),
        ('Транспорт', '2023-10-31', 1)
    ])
    def test_spending_by_category_valid_data(self, category, date, expected_rows):
        """Параметризованный тест для корректных данных"""
        result = spending_by_category(self.test_transactions_df, category, date)

        self.assertEqual(len(result), expected_rows)
        self.assertTrue('Месяц' in result.columns)
        self.assertTrue('Сумма' in result.columns)

    def test_spending_by_category_empty_dataframe(self):
        """Тест с пустым DataFrame"""
        empty_df = pd.DataFrame()
        result = spending_by_category(empty_df, self.category, self.date)
        self.assertTrue(result.empty)

    def test_spending_by_category_missing_columns(self):
        """Тест с отсутствующими обязательными колонками"""
        partial_df = self.test_transactions_df.drop('Категория', axis=1)
        result = spending_by_category(partial_df, self.category, self.date)
        self.assertTrue(result.empty)

    def test_spending_by_category_invalid_date_format(self):
        """Тест с некорректным форматом даты"""
        with patch('logging.getLogger') as mock_get_logger:
            mock_logger = Mock()
            mock_get_logger.return_value = mock_logger

            result = spending_by_category(
                self.test_transactions_df,
                self.category,
                'некорректная_дата'
            )
            self.assertTrue(result.empty)
            mock_logger.error.assert_called()

    @patch('src.reports.save_report_to_file')
    def test_spending_by_category_with_decorator(self, mock_decorator):
        """Тест работы с декоратором сохранения отчёта"""
        mock_decorator.return_value = lambda func: func
        result = spending_by_category(self.test_transactions_df, self.category, self.date)
        self.assertFalse(result.empty)

    # Тесты для spending_by_weekday
    def test_spending_by_weekday_valid_data(self):
        """Тест корректных данных для трат по дням недели"""
        result = spending_by_weekday(self.test_transactions_with_dates, self.date)
        self.assertEqual(len(result), 7)  # Все дни недели
        self.assertTrue('День недели' in result.columns)
        self.assertTrue('Средняя сумма' in result.columns)

    def test_spending_by_weekday_empty_dataframe(self):
        """Тест с пустым DataFrame"""
        empty_df = pd.DataFrame()
        result = spending_by_weekday(empty_df, self.date)
        self.assertTrue(result.empty)

    def test_spending_by_weekday_missing_columns(self):
        """Тест с отсутствующими колонками"""
        partial_df = self.test_transactions_with_dates.drop('Сумма операции', axis=1)
        result = spending_by_weekday(partial_df, self.date)
        self.assertTrue(result.empty)

    def test_spending_by_weekday_invalid_date(self):
        """Тест с некорректной датой"""
        with patch('logging.getLogger') as mock_get_logger:
            mock_logger = Mock()
            mock_get_logger.return_value = mock_logger

            result = spending_by_weekday(self.test_transactions_with_dates, 'некорректная_дата')
            self.assertTrue(result.empty)
            mock_logger.error.assert_called()

    # Тесты для spending_by_workday
    def test_spending_by_workday_valid_data(self):
        """Тест корректных данных для трат в рабочие/выходные дни"""
        result = spending_by_workday(self.test_transactions_with_dates, self.date)
        self.assertEqual(len(result), 2)  # Рабочий и выходной день
        self.assertTrue('Тип дня' in result.columns)
        self.assertTrue('Средняя сумма' in result.columns)
        # Проверяем наличие обеих категорий
        types = result['Тип дня'].tolist()
        self.assertIn('Рабочий день', types)
        self.assertIn('Выходной день', types)

    def test_spending_by_workday_only_weekdays(self):
        """Тест когда есть только рабочие дни"""
        weekdays_only = self.test_transactions_with_dates[
            ~self.test_transactions_with_dates['Дата операции'].isin(['2023-10-21', '2023-10-22'])
        ]
        result = spending_by_workday(weekdays_only, self.date)
        types = result['Тип дня'].tolist()
        self.assertIn('Рабочий день', types)
        self.assertIn('Выходной день', types)  # Должен быть с суммой 0.0

        def test_spending_by_workday_only_weekends(self):
            """Тест когда есть только выходные дни"""
            weekends_only = self.test_transactions_with_dates[
                self.test_transactions_with_dates['Дата операции'].isin(['2023-10-21', '2023-10-22'])
            ]
            result = spending_by_workday(weekends_only, self.date)
            types = result['Тип дня'].tolist()
            self.assertIn('Рабочий день', types)  # Должен быть с суммой 0.0
            self.assertIn('Выходной день', types)

            # Проверяем, что рабочий день имеет сумму 0.0
            workday_row = result[result['Тип дня'] == 'Рабочий день']
            self.assertEqual(workday_row['Средняя сумма'].iloc[0], 0.0)

        def test_spending_by_workday_empty_dataframe(self):
            """Тест с пустым DataFrame"""
            empty_df = pd.DataFrame()
            result = spending_by_workday(empty_df, self.date)
            self.assertTrue(result.empty)

        def test_spending_by_workday_missing_columns(self):
            """Тест с отсутствующими обязательными колонками"""
            partial_df = self.test_transactions_with_dates.drop('Сумма операции', axis=1)
            result = spending_by_workday(partial_df, self.date)
            self.assertTrue(result.empty)

        def test_spending_by_workday_invalid_date(self):
            """Тест с некорректной датой"""
            with patch('logging.getLogger') as mock_get_logger:
                mock_logger = Mock()
                mock_get_logger.return_value = mock_logger

                result = spending_by_workday(self.test_transactions_with_dates, 'некорректная_дата')
                self.assertTrue(result.empty)
                mock_logger.error.assert_called()

        # Тесты для декоратора save_report_to_file
        @patch('os.path.exists')
        @patch('builtins.open', new_callable=Mock)
        @patch('json.dumps')
        def test_save_report_decorator_success(self, mock_json_dumps, mock_open, mock_path_exists):
            """Тест успешного сохранения отчёта через декоратор"""
            # Настраиваем моки
            mock_path_exists.return_value = False
            mock_json_dumps.return_value = '{"test": "data"}'

            # Создаём тестовую функцию с декоратором
            @save_report_to_file("test_report.json")
            def test_func():
                return pd.DataFrame({'col1': [1, 2], 'col2': ['a', 'b']})

            result = test_func()

            # Проверяем вызовы
            mock_open.assert_called_once_with("test_report.json", 'w', encoding='utf-8')
            mock_json_dumps.assert_called_once()
            self.assertFalse(result.empty)

        @patch('os.path.exists')
        @patch('builtins.open')
        def test_save_report_decorator_empty_df(self, mock_open, mock_path_exists):
            """Тест декоратора с пустым DataFrame"""
            mock_path_exists.return_value = False

            @save_report_to_file("test_report.json")
            def test_func():
                return pd.DataFrame()

            with patch('logging.getLogger') as mock_get_logger:
                mock_logger = Mock()
                mock_get_logger.return_value = mock_logger

                result = test_func()
                self.assertTrue(result.empty)
                mock_logger.warning.assert_called_with(
                    "Не сохранён отчёт test_func — пустой DataFrame"
                )
                # Файл не должен быть создан
                mock_open.assert_not_called()

        @patch('os.path.exists')
        @patch('builtins.open')
        def test_save_report_decorator_filename_conflict(self, mock_open, mock_path_exists):
            """Тест обработки конфликта имён файлов"""
            # Первый вызов — файл существует, второй — нет
            mock_path_exists.side_effect = [True, False]

            @save_report_to_file("existing_file.json")
            def test_func():
                return pd.DataFrame({'data': [1]})

            test_func()

            # Должен попытаться сохранить как existing_file_1.json
            mock_open.assert_called_with("existing_file_1.json", 'w', encoding='utf-8')

        @patch('os.path.exists')
        @patch('builtins.open')
        def test_save_report_decorator_auto_filename(self, mock_open, mock_path_exists):
            """Тест автоматического формирования имени файла"""
            mock_path_exists.return_value = False

            @save_report_to_file()
            def another_test_func():
                return pd.DataFrame({'test': [1]})

            another_test_func()

            # Проверяем, что имя файла содержит имя функции и timestamp
            called_filename = mock_open.call_args[0][0]
            self.assertIn("another_test_func", called_filename)
            self.assertIn(".json", called_filename)

        @patch('logging.getLogger')
        def test_decorator_logging_calls(self, mock_get_logger):
            """Тест логирования в декораторе"""
            mock_logger = Mock()
            mock_get_logger.return_value = mock_logger

            @save_report_to_file("log_test.json")
            def logging_test_func():
                return pd.DataFrame({'log': [1]})

            logging_test_func()

            # Проверяем логирование успешного сохранения
            info_calls = [call[0][0] for call in mock_logger.info.call_args_list]
            self.assertTrue(any("Отчёт сохранён в файл" in call for call in info_calls))

        # Дополнительные параметризованные тесты
        @parameterized.expand([
            (None, 3),  # Текущая дата
            ('2023-09-30', 2),  # Конкретная дата
        ])
        def test_spending_by_category_with_different_dates(self, date_input, expected_rows):
            """Параметризованный тест для разных дат"""
            result = spending_by_category(self.test_transactions_df, 'Продукты', date_input)
            self.assertEqual(len(result), expected_rows)

        @parameterized.expand([
            ('2023-10-15', 7),  # Дата в середине периода
            ('2023-07-01', 4),  # Ранняя дата — меньше данных
        ])
        def test_spending_by_weekday_with_different_dates(self, date_input, expected_rows):
            """Параметризованный тест для трат по дням недели с разными датами"""
            result = spending_by_weekday(self.test_transactions_with_dates, date_input)
            self.assertEqual(len(result), expected_rows)

        # Тест обработки ошибок в декораторе
        @patch('os.path.exists')
        @patch('builtins.open')
        @patch('json.dumps')
        def test_save_report_decorator_json_error(self, mock_json_dumps, mock_open, mock_path_exists):
            """Тест обработки ошибки при преобразовании в JSON"""
            mock_path_exists.return_value = False
            mock_json_dumps.side_effect = Exception("JSON error")

            @save_report_to_file("error_test.json")
            def error_func():
                return pd.DataFrame({'problem': [1]})

            with patch('logging.getLogger') as mock_get_logger:
                mock_logger = Mock()
                mock_get_logger.return_value = mock_logger

                with self.assertRaises(Exception) as context:
                    error_func()
                self.assertIn("Ошибка при преобразовании DataFrame в JSON", str(context.exception))
                mock_logger.error.assert_called()

    if __name__ == '__main__':
        unittest.main()
