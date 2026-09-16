import json
from datetime import datetime
from unittest.mock import Mock

import pandas as pd
import pytest

from src.views import (
    filter_transactions_by_month,
    get_cards_info,
    get_greeting,
    get_top_transactions,
    main_page,
)


@pytest.mark.parametrize(
    ("date_string", "expected"),
    [
        ("2021-12-31 05:59:59", "Доброй ночи"),
        ("2021-12-31 06:00:00", "Доброе утро"),
        ("2021-12-31 11:59:59", "Доброе утро"),
        ("2021-12-31 12:00:00", "Добрый день"),
        ("2021-12-31 17:59:59", "Добрый день"),
        ("2021-12-31 18:00:00", "Добрый вечер"),
        ("2021-12-31 22:59:59", "Добрый вечер"),
        ("2021-12-31 23:00:00", "Доброй ночи"),
    ],
)
def test_get_greeting(date_string: str, expected: str) -> None:
    """Проверяет приветствие на границах временных интервалов."""

    current_datetime = datetime.fromisoformat(date_string)

    assert get_greeting(current_datetime) == expected


def test_filter_transactions_by_month() -> None:
    """Проверяет выбор транзакций с начала месяца по указанное время."""

    transactions = pd.DataFrame(
        {
            "Дата операции": [
                "30.11.2021 23:59:59",
                "01.12.2021 00:00:00",
                "15.12.2021 12:00:00",
                "15.12.2021 12:00:01",
                "01.01.2022 00:00:00",
            ],
            "Описание": [
                "Предыдущий месяц",
                "Начало месяца",
                "Граница периода",
                "После границы",
                "Следующий месяц",
            ],
        }
    )

    result = filter_transactions_by_month(
        transactions,
        datetime.fromisoformat("2021-12-15 12:00:00"),
    )

    assert result["Описание"].tolist() == [
        "Начало месяца",
        "Граница периода",
    ]


def test_get_cards_info() -> None:
    """Проверяет расчет расходов и кешбэка по картам."""

    transactions = pd.DataFrame(
        [
            {
                "Номер карты": "*1234",
                "Статус": "OK",
                "Сумма платежа": -100.49,
            },
            {
                "Номер карты": "*1234",
                "Статус": "OK",
                "Сумма платежа": -50.0,
            },
            {
                "Номер карты": "*5678",
                "Статус": "OK",
                "Сумма платежа": -200.0,
            },
            {
                "Номер карты": "*1234",
                "Статус": "FAILED",
                "Сумма платежа": -1000.0,
            },
            {
                "Номер карты": None,
                "Статус": "OK",
                "Сумма платежа": -300.0,
            },
            {
                "Номер карты": "*5678",
                "Статус": "OK",
                "Сумма платежа": 500.0,
            },
        ]
    )

    result = get_cards_info(transactions)

    assert result == [
        {
            "last_digits": "1234",
            "total_spent": 150.49,
            "cashback": 1.5,
        },
        {
            "last_digits": "5678",
            "total_spent": 200.0,
            "cashback": 2.0,
        },
    ]


def test_get_cards_info_without_expenses() -> None:
    """Проверяет результат при отсутствии карточных расходов."""

    transactions = pd.DataFrame(
        [
            {
                "Номер карты": "*1234",
                "Статус": "OK",
                "Сумма платежа": 500.0,
            },
            {
                "Номер карты": "*5678",
                "Статус": "FAILED",
                "Сумма платежа": -200.0,
            },
        ]
    )

    assert get_cards_info(transactions) == []


def test_get_top_transactions() -> None:
    """Проверяет сортировку и формат крупнейших транзакций."""

    transactions = pd.DataFrame(
        {
            "Дата операции": [
                "01.01.2021 10:00:00",
                "02.01.2021 10:00:00",
                "03.01.2021 10:00:00",
                "04.01.2021 10:00:00",
                "05.01.2021 10:00:00",
                "06.01.2021 10:00:00",
                "07.01.2021 10:00:00",
            ],
            "Статус": [
                "OK",
                "OK",
                "OK",
                "OK",
                "OK",
                "OK",
                "FAILED",
            ],
            "Сумма платежа": [
                -100.0,
                500.0,
                -300.0,
                50.0,
                -700.0,
                -200.0,
                -9999.0,
            ],
            "Категория": [
                "Категория 1",
                "Категория 2",
                "Категория 3",
                "Категория 4",
                "Категория 5",
                "Категория 6",
                "Категория 7",
            ],
            "Описание": [
                "Операция 1",
                "Операция 2",
                "Операция 3",
                "Операция 4",
                "Операция 5",
                "Операция 6",
                "Неуспешная операция",
            ],
        }
    )

    result = get_top_transactions(transactions)

    assert len(result) == 5
    assert [transaction["amount"] for transaction in result] == [
        700.0,
        500.0,
        300.0,
        200.0,
        100.0,
    ]
    assert result[0] == {
        "date": "05.01.2021",
        "amount": 700.0,
        "category": "Категория 5",
        "description": "Операция 5",
    }


@pytest.mark.parametrize("limit", [0, -1])
def test_get_top_transactions_with_non_positive_limit(limit: int) -> None:
    """Проверяет пустой результат при неположительном ограничении."""

    assert get_top_transactions(pd.DataFrame(), limit) == []


def test_main_page(
    monkeypatch: pytest.MonkeyPatch,
    sample_transactions: pd.DataFrame,
) -> None:
    """Проверяет формирование полного JSON-ответа главной страницы."""

    load_transactions_mock = Mock(return_value=sample_transactions)
    load_settings_mock = Mock(
        return_value={
            "user_currencies": ["USD"],
            "user_stocks": ["AAPL"],
        }
    )
    currency_rates_mock = Mock(
        return_value=[
            {
                "currency": "USD",
                "rate": 80.0,
            }
        ]
    )
    stock_prices_mock = Mock(
        return_value=[
            {
                "stock": "AAPL",
                "price": 150.0,
            }
        ]
    )

    monkeypatch.setattr(
        "src.views.load_transactions",
        load_transactions_mock,
    )
    monkeypatch.setattr(
        "src.views.load_user_settings",
        load_settings_mock,
    )
    monkeypatch.setattr(
        "src.views.get_currency_rates",
        currency_rates_mock,
    )
    monkeypatch.setattr(
        "src.views.get_stock_prices",
        stock_prices_mock,
    )

    result = main_page("2021-01-31 12:00:00")
    response = json.loads(result)

    assert response == {
        "greeting": "Добрый день",
        "cards": [
            {
                "last_digits": "1234",
                "total_spent": 150.0,
                "cashback": 1.5,
            }
        ],
        "top_transactions": [
            {
                "date": "01.01.2021",
                "amount": 150.0,
                "category": "Супермаркеты",
                "description": "Магазин",
            }
        ],
        "currency_rates": [
            {
                "currency": "USD",
                "rate": 80.0,
            }
        ],
        "stock_prices": [
            {
                "stock": "AAPL",
                "price": 150.0,
            }
        ],
    }
    assert "Добрый день" in result

    load_transactions_mock.assert_called_once_with()
    load_settings_mock.assert_called_once_with()
    currency_rates_mock.assert_called_once_with(["USD"])
    stock_prices_mock.assert_called_once_with(["AAPL"])


def test_main_page_invalid_date() -> None:
    """Проверяет ошибку при некорректном формате входящей даты."""

    with pytest.raises(
        ValueError,
        match="YYYY-MM-DD HH:MM:SS",
    ):
        main_page("31.12.2021")
