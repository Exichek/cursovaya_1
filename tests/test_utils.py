import json
from pathlib import Path
from unittest.mock import Mock, call

import pandas as pd
import pytest
import requests

from src.utils import (
    API_TIMEOUT,
    CURRENCY_API_URL,
    STOCK_API_URL,
    get_currency_rates,
    get_stock_prices,
    load_transactions,
    load_user_settings,
)


def test_load_transactions_success(
    tmp_path: Path,
    sample_transactions: pd.DataFrame,
) -> None:
    """Проверяет успешную загрузку и преобразование дат."""

    file_path = tmp_path / "operations.xlsx"
    sample_transactions.to_excel(file_path, index=False)

    result = load_transactions(file_path)

    assert len(result) == 2
    assert pd.api.types.is_datetime64_any_dtype(result["Дата операции"])
    assert pd.api.types.is_datetime64_any_dtype(result["Дата платежа"])
    assert pd.isna(result.loc[1, "Дата платежа"])


def test_load_transactions_file_not_found(tmp_path: Path) -> None:
    """Проверяет ошибку при отсутствии Excel-файла."""

    file_path = tmp_path / "missing.xlsx"

    with pytest.raises(FileNotFoundError, match="Файл с транзакциями не найден"):
        load_transactions(file_path)


def test_load_transactions_missing_columns(tmp_path: Path) -> None:
    """Проверяет ошибку при отсутствии обязательных столбцов."""

    file_path = tmp_path / "operations.xlsx"
    pd.DataFrame({"Дата операции": ["01.01.2021 12:30:00"]}).to_excel(
        file_path,
        index=False,
    )

    with pytest.raises(ValueError, match="Отсутствуют обязательные столбцы"):
        load_transactions(file_path)


def test_load_transactions_invalid_date(
    tmp_path: Path,
    sample_transactions: pd.DataFrame,
) -> None:
    """Проверяет ошибку при некорректной дате операции."""

    file_path = tmp_path / "operations.xlsx"
    invalid_transactions = sample_transactions.copy()
    invalid_transactions.loc[0, "Дата операции"] = "неправильная дата"
    invalid_transactions.to_excel(file_path, index=False)

    with pytest.raises(ValueError, match="содержит некорректные даты"):
        load_transactions(file_path)


def test_load_transactions_read_error(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Проверяет обработку ошибки чтения Excel-файла."""

    file_path = tmp_path / "operations.xlsx"
    file_path.touch()

    def raise_read_error(*args: object, **kwargs: object) -> pd.DataFrame:
        raise OSError("Ошибка чтения")

    monkeypatch.setattr(pd, "read_excel", raise_read_error)

    with pytest.raises(ValueError, match="Не удалось прочитать файл"):
        load_transactions(file_path)


def test_load_user_settings_success(tmp_path: Path) -> None:
    """Проверяет загрузку и нормализацию пользовательских настроек."""

    file_path = tmp_path / "user_settings.json"
    file_path.write_text(
        json.dumps(
            {
                "user_currencies": ["usd", "eur"],
                "user_stocks": ["aapl", "msft"],
            }
        ),
        encoding="utf-8",
    )

    assert load_user_settings(file_path) == {
        "user_currencies": ["USD", "EUR"],
        "user_stocks": ["AAPL", "MSFT"],
    }


def test_load_user_settings_file_not_found(tmp_path: Path) -> None:
    """Проверяет ошибку при отсутствии файла настроек."""

    with pytest.raises(FileNotFoundError, match="Файл настроек не найден"):
        load_user_settings(tmp_path / "missing.json")


def test_load_user_settings_invalid_json(tmp_path: Path) -> None:
    """Проверяет обработку некорректного JSON."""

    file_path = tmp_path / "user_settings.json"
    file_path.write_text("{invalid json", encoding="utf-8")

    with pytest.raises(ValueError, match="Не удалось загрузить настройки"):
        load_user_settings(file_path)


@pytest.mark.parametrize(
    ("settings", "error_message"),
    [
        ([], "JSON-объектом"),
        (
            {
                "user_currencies": ["USD", 123],
                "user_stocks": ["AAPL"],
            },
            "user_currencies",
        ),
        (
            {
                "user_currencies": ["USD"],
                "user_stocks": ["AAPL", 123],
            },
            "user_stocks",
        ),
    ],
)
def test_load_user_settings_invalid_structure(
    tmp_path: Path,
    settings: object,
    error_message: str,
) -> None:
    """Проверяет структуру пользовательских настроек."""

    file_path = tmp_path / "user_settings.json"
    file_path.write_text(json.dumps(settings), encoding="utf-8")

    with pytest.raises(ValueError, match=error_message):
        load_user_settings(file_path)


def test_get_currency_rates_success(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Проверяет получение и преобразование курсов валют."""

    response = Mock()
    response.json.return_value = {
        "data": {
            "USD": {"value": 0.0125},
            "EUR": {"value": 0.01},
        }
    }

    request_mock = Mock(return_value=response)
    monkeypatch.setattr("src.utils.requests.get", request_mock)

    result = get_currency_rates(["USD", "EUR"], api_key="test-key")

    assert result == [
        {"currency": "USD", "rate": 80.0},
        {"currency": "EUR", "rate": 100.0},
    ]
    request_mock.assert_called_once_with(
        CURRENCY_API_URL,
        headers={"apikey": "test-key"},
        params={
            "base_currency": "RUB",
            "currencies": "USD,EUR",
        },
        timeout=API_TIMEOUT,
    )
    response.raise_for_status.assert_called_once_with()


def test_get_currency_rates_partial_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Проверяет обработку некорректного курса отдельной валюты."""

    response = Mock()
    response.json.return_value = {
        "data": {
            "USD": {"value": 0.0125},
            "EUR": {"value": 0},
        }
    }

    monkeypatch.setattr(
        "src.utils.requests.get",
        Mock(return_value=response),
    )

    assert get_currency_rates(
        ["USD", "EUR"],
        api_key="test-key",
    ) == [
        {"currency": "USD", "rate": 80.0},
        {"currency": "EUR", "rate": 0.0},
    ]


def test_get_currency_rates_request_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Проверяет обработку сетевой ошибки сервиса валют."""

    monkeypatch.setattr(
        "src.utils.requests.get",
        Mock(side_effect=requests.RequestException("Ошибка сети")),
    )

    assert get_currency_rates(
        ["USD", "EUR"],
        api_key="test-key",
    ) == [
        {"currency": "USD", "rate": 0.0},
        {"currency": "EUR", "rate": 0.0},
    ]


def test_get_stock_prices_success(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Проверяет получение стоимости акций."""

    first_response = Mock()
    first_response.json.return_value = {"c": 150.125}

    second_response = Mock()
    second_response.json.return_value = {"c": 300.999}

    request_mock = Mock(side_effect=[first_response, second_response])
    monkeypatch.setattr("src.utils.requests.get", request_mock)

    result = get_stock_prices(
        ["AAPL", "MSFT"],
        api_key="test-key",
    )

    assert result == [
        {"stock": "AAPL", "price": 150.12},
        {"stock": "MSFT", "price": 301.0},
    ]
    assert request_mock.call_args_list == [
        call(
            STOCK_API_URL,
            headers={"X-Finnhub-Token": "test-key"},
            params={"symbol": "AAPL"},
            timeout=API_TIMEOUT,
        ),
        call(
            STOCK_API_URL,
            headers={"X-Finnhub-Token": "test-key"},
            params={"symbol": "MSFT"},
            timeout=API_TIMEOUT,
        ),
    ]
    first_response.raise_for_status.assert_called_once_with()
    second_response.raise_for_status.assert_called_once_with()


def test_get_stock_prices_errors(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Проверяет независимую обработку ошибок для каждой акции."""

    zero_response = Mock()
    zero_response.json.return_value = {"c": 0}

    valid_response = Mock()
    valid_response.json.return_value = {"c": 500.0}

    monkeypatch.setattr(
        "src.utils.requests.get",
        Mock(
            side_effect=[
                requests.RequestException("Ошибка сети"),
                zero_response,
                valid_response,
            ]
        ),
    )

    assert get_stock_prices(
        ["AAPL", "TSLA", "MSFT"],
        api_key="test-key",
    ) == [
        {"stock": "AAPL", "price": 0.0},
        {"stock": "TSLA", "price": 0.0},
        {"stock": "MSFT", "price": 500.0},
    ]


def test_api_functions_without_keys(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Проверяет обработку отсутствующих API-ключей."""

    monkeypatch.delenv("CURRENCY_API_KEY", raising=False)
    monkeypatch.delenv("STOCK_API_KEY", raising=False)

    assert get_currency_rates(["USD"]) == [{"currency": "USD", "rate": 0.0}]
    assert get_stock_prices(["AAPL"]) == [{"stock": "AAPL", "price": 0.0}]


def test_api_functions_with_empty_lists() -> None:
    """Проверяет вызов API-функций без валют и акций."""

    assert get_currency_rates([], api_key="test-key") == []
    assert get_stock_prices([], api_key="test-key") == []
