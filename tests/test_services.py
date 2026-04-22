import unittest
from unittest.mock import patch, Mock
from parameterized import parameterized
import pandas as pd
from datetime import datetime
from src.services import (
    calculate_cashback_categories,
    investment_bank,
    simple_transaction_search,
    transactions_with_phone_numbers,
    transfers_to_individuals,
    find_column_in_dict,
    log_service_start
)

class TestServices(unittest.TestCase):

    # Фикстура для тестовых данных
    @classmethod
    def setUpClass(cls):
        """Создаёт тестовые данные один раз для всех тестов"""
        cls.test_transactions_df = pd.DataFrame([
            {
                'Дата платежа': '2023-10-15',
                'Категория': 'Продукты',
                'Сумма операции': 123.50,
                'Кэшбэк': True
            },
            {
                'Дата платежа': '2023-10-20',
                'Категория': 'Развлечения',
                'Сумма операции': 87.25,
                'Кэшбэк': True
            },
            {
                'Дата платежа': '2023-11-05',
                'Категория': 'Транспорт',
                'Сумма операции': 250.75,
                'Кэшбэк': False
            },
            {
                'Дата платежа': '2023-10-25',
                'Категория': 'Продукты',
                'Сумма операции': 99.99,
                'Кэшбэк': True
            }
        ])

        cls.test_transactions_list = [
            {
                "Дата операции": "2023-10-15",
                "Сумма операции": 123.50
            },
            {
                "Дата операции": "2023-10-20",
                "Сумма операции": 87.25
            },
            {
                "Дата операции": "2023-11-05",
                "Сумма операции": 250.75
            },
            {
                "Дата операции": "2023-10-25",
                "Сумма операции": 99.99
            }
        ]

    def setUp(self):
        """Выполняется перед каждым тестом"""
        self.year = 2023
        self.month = 10

    # Тесты для find_column_in_dict
    def test_find_column_in_dict_found(self):
        """Тест нахождения ключа в словаре"""
        transaction = {'Дата платежа': '2023-10-15', 'Сумма': 100.0}
        result = find_column_in_dict(transaction, ['Дата платежа', 'Date'])
        self.assertEqual(result, '2023-10-15')

    def test_find_column_in_dict_not_found(self):
        """Тест когда ключ не найден"""
        transaction = {'Дата': '2023-10-15'}
        result = find_column_in_dict(transaction, ['Дата платежа', 'Payment Date'])
        self.assertIsNone(result)

    # Тесты для log_service_start
    @patch('logging.getLogger')
    def test_log_service_start(self, mock_get_logger):
        """Тест логирования запуска сервиса"""
        mock_logger = Mock()
        mock_get_logger.return_value = mock_logger

        log_service_start("test_service", param1="value1", param2=42)
        mock_logger.info.assert_called_once()

    # Тесты для calculate_cashback_categories
    @parameterized.expand([
        (2023, 10, 300.74),  # Октябрь 2023
        (2023, 11, 0.0),     # Ноябрь 2023 — нет кешбэка
        (2024, 10, 0.0)     # Другой год
    ])
    def test_calculate_cashback_categories(self, year, month, expected_total):
        """Параметризованный тест для расчёта кешбэка"""
        result = calculate_cashback_categories(year, month, self.test_transactions_df)

        if expected_total > 0:
            self.assertEqual(result['year'], year)
            self.assertEqual(result['month'], month)
            self.assertAlmostEqual(result['total_amount'], expected_total, places=2)
            self.assertEqual(result['status'], 'success')
        else:
            self.assertEqual(result['total_amount'], 0.0)

    def test_calculate_cashback_empty_dataframe(self):
        """Тест с пустым DataFrame"""
        empty_df = pd.DataFrame()
        result = calculate_cashback_categories(2023, 10, empty_df)
        self.assertEqual(result['status'], 'success')
        self.assertEqual(result['total_amount'], 0.0)

    def test_calculate_cashback_invalid_month(self):
        """Тест с некорректным месяцем"""
        with patch('logging.getLogger') as mock_get_logger:
            mock_logger = Mock()
            mock_get_logger.return_value = mock_logger

            result = calculate_cashback_categories(2023, 13, self.test_transactions_df)
            self.assertEqual(result['status'], 'error')
            mock_logger.error.assert_called()

    # Тесты для investment_bank
    @parameterized.expand([
        ("2023-10", 10, 9.26),
        ("2023-10", 50, 22.51),
        ("2023-10", 100, 77.51)
    ])
    def test_investment_bank_with_different_limits(self, month, limit, expected_sum):
        """Параметризованный тест для разных лимитов округления"""
        result = investment_bank(month, self.test_transactions_list, limit)
        self.assertAlmostEqual(result, expected_sum, places=2)

    def test_investment_bank_empty_transactions(self):
        """Тест с пустым списком транзакций"""
        result = investment_bank("2023-10", [], 10)
        self.assertEqual(result, 0.0)

    def test_investment_bank_invalid_limit(self):
        """Тест с некорректным лимитом"""
        with patch('logging.getLogger') as mock_get_logger:
            mock_logger = Mock()
            mock_get_logger.return_value = mock_logger

            result = investment_bank("2023-10", self.test_transactions_list, 25)
            self.assertEqual(result, 0.0)
            mock_logger.error.assert_called()

    def test_investment_bank_invalid_month_format(self):
        """Тест с некорректным форматом месяца"""
        with patch('logging.getLogger') as mock_get_logger:
            mock_logger = Mock()
            mock_get_logger.return_value = mock_logger

            result = investment_bank("2023/10", self.test_transactions_list, 10)
            self.assertEqual(result, 0.0)
            mock_logger.error.assert_called()

    # Тесты для simple_transaction_search
    def test_simple_transaction_search_specific_column(self):
        """Поиск в конкретной колонке"""
        result = simple_transaction_search(
            self.test_transactions_df,
            'Продукты',
            'Категория'
        )
        self.assertEqual(len(result), 2)
        self.assertTrue(all(result['Категория'] == 'Продукты'))

    def test_simple_transaction_search_all_columns(self):
        """Поиск по всем колонкам"""
        result = simple_transaction_search(self.test_transactions_df, '2023-10')
        self.assertEqual(len(result), 3)  # 3 транзакции в октябре

        def test_simple_transaction_search_not_found(self):
            """Поиск, когда ничего не найдено"""
            result = simple_transaction_search(
                self.test_transactions_df,
                'несуществующий_термин',
                'Категория'
            )
            self.assertEqual(len(result), 0)

        def test_simple_transaction_search_column_not_found(self):
            """Тест с несуществующей колонкой"""
            with self.assertRaises(ValueError) as context:
                simple_transaction_search(
                    self.test_transactions_df,
                    'поиск',
                    'несуществующая_колонка'
                )
            self.assertIn('Колонка \'несуществующая_колонка\' не найдена', str(context.exception))

        # Тесты для transactions_with_phone_numbers
        def test_transactions_with_phone_numbers_found(self):
            """Тест нахождения телефонных номеров"""
            # Создаём DataFrame с телефонными номерами
            df_with_phones = pd.DataFrame([
                {
                    'Дата платежа': '2023-10-15',
                    'Категория': 'Перевод',
                    'Сумма операции': 1000.0,
                    'Комментарий': 'Перевод +79161234567'
                },
                {
                    'Дата платежа': '2023-10-20',
                    'Категория': 'Оплата',
                    'Сумма операции': 500.0,
                    'Комментарий': 'Оплата 89167654321'
                }
            ])

            result = transactions_with_phone_numbers(df_with_phones)
            self.assertEqual(len(result), 2)
            self.assertTrue('Найденный номер' in result.columns)
            self.assertTrue(any('+79161234567' in str(num) for num in result['Найденный номер']))

        def test_transactions_with_phone_numbers_not_found(self):
            """Тест когда номера не найдены"""
            result = transactions_with_phone_numbers(self.test_transactions_df)
            self.assertEqual(len(result), 0)

        # Тесты для transfers_to_individuals
        def test_transfers_to_individuals_found(self):
            """Тест нахождения переводов физлицам"""
            # Создаём DataFrame с переводами физлицам
            df_with_transfers = pd.DataFrame([
                {
                    'Дата платежа': '2023-10-15',
                    'Категория': 'Перевод',
                    'Сумма операции': 1500.0,
                    'Описание': 'Перевод физлицу Иванову И.И.'
                },
                {
                    'Дата платежа': '2023-10-20',
                    'Категория': 'Оплата',
                    'Сумма операции': 800.0,
                    'Описание': 'Перевести деньги на карту'
                }
            ])

            result = transfers_to_individuals(df_with_transfers)
            self.assertEqual(len(result), 2)
            self.assertTrue('Ключевое слово' in result.columns)

        def test_transfers_to_individuals_not_found(self):
            """Тест когда переводы физлицам не найдены"""
            result = transfers_to_individuals(self.test_transactions_df)
            self.assertEqual(len(result), 0)

        # Дополнительные тесты с моками для проверки логирования
        @patch('logging.getLogger')
        def test_investment_bank_logging_calls(self, mock_get_logger):
            """Тест проверяет, что функция делает вызовы логирования"""
            mock_logger = Mock()
            mock_get_logger.return_value = mock_logger

            investment_bank("2023-10", self.test_transactions_list, 10)

            # Проверяем, что были вызовы логирования
            self.assertTrue(mock_logger.info.called)
            # Должен быть как минимум запуск и завершение
            info_calls = [call[0][0] for call in mock_logger.info.call_args_list]
            self.assertTrue(any("Запуск сервиса 'investment_bank'" in call for call in info_calls))
            self.assertTrue(any("Расчёт Инвесткопилки завершён" in call for call in info_calls))

        @patch('logging.getLogger')
        def test_calculate_cashback_categories_logging(self, mock_get_logger):
            """Тест логирования в calculate_cashback_categories"""
            mock_logger = Mock()
            mock_get_logger.return_value = mock_logger

            calculate_cashback_categories(2023, 10, self.test_transactions_df)

            self.assertTrue(mock_logger.info.called)
            info_calls = [call[0][0] for call in mock_logger.info.call_args_list]
            self.assertTrue(any("Запуск сервиса 'calculate_cashback_categories'" in call for call in info_calls))
            self.assertTrue(any("Расчёт кешбэка завершён" in call for call in info_calls))

        # Тест обработки ошибок в transfers_to_individuals
        @patch('logging.getLogger')
        def test_transfers_to_individuals_with_errors(self, mock_get_logger):
            """Тест обработки ошибок в transfers_to_individuals"""
            mock_logger = Mock()
            mock_get_logger.return_value = mock_logger

            # Создаём DataFrame с некорректными данными в одной колонке
            problematic_df = pd.DataFrame([
                {'Дата платежа': '2023-10-15', 'Описание': 'Перевод физлицу'},
                {'Дата платежа': '2023-10-20', 'Описание': None}  # None вызовет ошибку при поиске
            ])

            result = transfers_to_individuals(problematic_df)
            self.assertEqual(len(result), 1)  # Должна быть найдена одна транзакция
            self.assertTrue(mock_logger.warning.called)  # Должна быть запись об ошибке

        # Тест крайних случаев для investment_bank
        def test_investment_bank_edge_cases(self):
            """Тест крайних случаев для Инвесткопилки"""
            edge_transactions = [
                {"Дата операции": "2023-10-01", "Сумма операции": 0.00},  # Нулевая сумма
                {"Дата операции": "2023-10-02", "Сумма операции": -50.00},  # Отрицательная сумма
                {"Дата операции": "2023-10-03", "Сумма операции": 100.00}  # Точное кратное
            ]

            result = investment_bank("2023-10", edge_transactions, 10)
            # Нулевая и отрицательная суммы дают 0, точное кратное даёт 0
            self.assertEqual(result, 0.0)

    if __name__ == '__main__':
        unittest.main()
