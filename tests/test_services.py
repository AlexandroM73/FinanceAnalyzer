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
            self.test_transactions_df, 'Не существующая категория'
        )
        self.assertEqual(len(result), 0)

    def test_simple_transaction_search_case_insensitive(self):
        """Поиск без учёта регистра"""
        result = simple_transaction_search(
            self.test_transactions_df,
            'продукты',  # в нижнем регистре
            'Категория'
        )
        self.assertEqual(len(result), 2)
        self.assertTrue(all(result['Категория'] == 'Продукты'))

        # Тесты для transactions_with_phone_numbers

    def test_transactions_with_phone_numbers_found(self):
        """Тест нахождения транзакций с номерами телефонов"""
        # Создаём DataFrame с номерами телефонов
        df_with_phones = self.test_transactions_df.copy()
        df_with_phones['Комментарий'] = [
            'Перевод +79161234567',
            'Оплата +79267654321',
            'Без номера',
            'Перевод +79031112233'
        ]

        result = transactions_with_phone_numbers(df_with_phones)
        self.assertEqual(len(result), 3)  # 3 транзакции с номерами
        # Проверяем, что все результаты содержат номера телефонов
        phone_pattern = r'\+7\d{10}'
        for comment in result['Комментарий']:
            self.assertRegex(comment, phone_pattern)

    def test_transactions_with_phone_numbers_not_found(self):
        """Тест когда номера телефонов не найдены"""
        # DataFrame без номеров телефонов
        df_no_phones = self.test_transactions_df.copy()
        df_no_phones['Комментарий'] = ['Без номера', 'Без номера', 'Без номера', 'Без номера']

        result = transactions_with_phone_numbers(df_no_phones)
        self.assertEqual(len(result), 0)

    def test_transactions_with_phone_numbers_empty_dataframe(self):
        """Тест с пустым DataFrame"""
        empty_df = pd.DataFrame()
        result = transactions_with_phone_numbers(empty_df)
        self.assertEqual(len(result), 0)

        # Тесты для transfers_to_individuals

    def test_transfers_to_individuals_found(self):
        """Тест нахождения переводов физлицам"""
        # Создаём DataFrame с переводами физлицам
        df_with_transfers = self.test_transactions_df.copy()
        df_with_transfers['Тип операции'] = [
            'Перевод',
            'Оплата',
            'Перевод физлицу',
            'Перевод Иванову И.И.'
        ]
        df_with_transfers['Получатель'] = [
            'Банк',
            'Магазин',
            'Петров А.С.',
            'Иванов И.И.'
        ]

        result = transfers_to_individuals(df_with_transfers)
        self.assertEqual(len(result), 2)  # 2 перевода физлицам
        expected_recipients = ['Петров А.С.', 'Иванов И.И.']
        self.assertListEqual(list(result['Получатель']), expected_recipients)

    def test_transfers_to_individuals_not_found(self):
        """Тест когда переводы физлицам не найдены"""
        # DataFrame без переводов физлицам
        df_no_transfers = self.test_transactions_df.copy()
        df_no_transfers['Тип операции'] = ['Оплата', 'Оплата', 'Оплата', 'Оплата']
        df_no_transfers['Получатель'] = ['Банк', 'Магазин', 'Сервис', 'Компания']

        result = transfers_to_individuals(df_no_transfers)
        self.assertEqual(len(result), 0)

    def test_transfers_to_individuals_empty_dataframe(self):
        """Тест с пустым DataFrame"""
        empty_df = pd.DataFrame()
        result = transfers_to_individuals(empty_df)
        self.assertEqual(len(result), 0)

        # Дополнительные тесты для edge cases

    def test_calculate_cashback_categories_edge_cases(self):
        """Тест крайних случаев для расчёта кешбэка"""
        # Тест с одной транзакцией
        single_transaction = pd.DataFrame([{
            'Дата платежа': '2023-10-15',
            'Категория': 'Продукты',
            'Сумма операции': 100.0,
            'Кэшбэк': True
        }])
        result = calculate_cashback_categories(2023, 10, single_transaction)
        self.assertEqual(result['total_amount'], 100.0)

        # Тест с нулевыми суммами
        zero_amount = pd.DataFrame([{
            'Дата платежа': '2023-10-15',
            'Категория': 'Продукты',
            'Сумма операции': 0.0,
            'Кэшбэк': True
        }])
        result = calculate_cashback_categories(2023, 10, zero_amount)
        self.assertEqual(result['total_amount'], 0.0)

    @patch('logging.getLogger')
    def test_investment_bank_logging_on_error(self, mock_get_logger):
        """Тест логирования ошибок в investment_bank"""
        mock_logger = Mock()
        mock_get_logger.return_value = mock_logger

        # Используем некорректный лимит, который должен вызвать ошибку
        result = investment_bank("2023-10", self.test_transactions_list, -5)
        self.assertEqual(result, 0.0)
        mock_logger.error.assert_called()


if __name__ == '__main__':
    unittest.main()
