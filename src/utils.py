import json
import logging
import os
from pathlib import Path
from typing import TypedDict

import pandas as pd
import requests
from dotenv import load_dotenv

logger = logging.getLogger(__name__)

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_OPERATIONS_PATH = PROJECT_ROOT / "data" / "operations.xlsx"

DEFAULT_SETTINGS_PATH = PROJECT_ROOT / "user_settings.json"

CURRENCY_API_URL = "https://api.currencyapi.com/v3/latest"
STOCK_API_URL = "https://finnhub.io/api/v1/quote"
API_TIMEOUT = 10

load_dotenv(PROJECT_ROOT / ".env")


class UserSettings(TypedDict):
    """Структура пользовательских настроек."""

    user_currencies: list[str]
    user_stocks: list[str]


class CurrencyRate(TypedDict):
    """Структура курса валюты."""

    currency: str
    rate: float


class StockPrice(TypedDict):
    """Структура стоимости акции."""

    stock: str
    price: float


REQUIRED_COLUMNS: frozenset[str] = frozenset(
    {
        "Дата операции",
        "Дата платежа",
        "Номер карты",
        "Статус",
        "Сумма операции",
        "Валюта операции",
        "Сумма платежа",
        "Валюта платежа",
        "Кэшбэк",
        "Категория",
        "MCC",
        "Описание",
        "Бонусы (включая кэшбэк)",
        "Округление на инвесткопилку",
        "Сумма операции с округлением",
    }
)

DATE_FORMATS: dict[str, str] = {
    "Дата операции": "%d.%m.%Y %H:%M:%S",
    "Дата платежа": "%d.%m.%Y",
}


def load_transactions(
    file_path: str | Path = DEFAULT_OPERATIONS_PATH,
) -> pd.DataFrame:
    """Загружает банковские транзакции из Excel-файла и преобразует даты."""

    path = Path(file_path)

    if not path.is_file():
        logger.error("Файл с транзакциями не найден: %s", path)
        raise FileNotFoundError(f"Файл с транзакциями не найден: {path}")

    try:
        transactions = pd.read_excel(path)
    except (OSError, ValueError) as error:
        logger.exception("Не удалось прочитать файл с транзакциями: %s", path)
        raise ValueError(f"Не удалось прочитать файл: {path}") from error

    missing_columns = REQUIRED_COLUMNS.difference(transactions.columns)

    if missing_columns:
        columns = ", ".join(sorted(missing_columns))
        logger.error("В файле отсутствуют обязательные столбцы: %s", columns)
        raise ValueError(f"Отсутствуют обязательные столбцы: {columns}")

    for column, date_format in DATE_FORMATS.items():
        source_dates = transactions[column]
        parsed_dates = pd.to_datetime(
            source_dates,
            format=date_format,
            errors="coerce",
        )

        invalid_dates = source_dates.notna() & parsed_dates.isna()

        if invalid_dates.any():
            logger.error(
                "В столбце «%s» обнаружено некорректных дат: %s",
                column,
                int(invalid_dates.sum()),
            )
            raise ValueError(f"Столбец «{column}» содержит некорректные даты")

        transactions[column] = parsed_dates

    logger.info("Загружено транзакций: %s", len(transactions))
    return transactions


def load_user_settings(
    file_path: str | Path = DEFAULT_SETTINGS_PATH,
) -> UserSettings:
    """Загружает и проверяет пользовательские настройки из JSON-файла."""

    path = Path(file_path)

    if not path.is_file():
        logger.error("Файл пользовательских настроек не найден: %s", path)
        raise FileNotFoundError(f"Файл настроек не найден: {path}")

    try:
        with path.open(encoding="utf-8") as file:
            settings = json.load(file)
    except (OSError, json.JSONDecodeError) as error:
        logger.exception("Не удалось загрузить настройки: %s", path)
        raise ValueError(f"Не удалось загрузить настройки: {path}") from error

    # Добавляем вот сюда
    if not isinstance(settings, dict):
        raise ValueError("Настройки должны быть JSON-объектом")

    currencies = settings.get("user_currencies")
    stocks = settings.get("user_stocks")

    if not isinstance(currencies, list) or not all(isinstance(currency, str) for currency in currencies):
        raise ValueError("Настройка user_currencies должна быть списком строк")

    if not isinstance(stocks, list) or not all(isinstance(stock, str) for stock in stocks):
        raise ValueError("Настройка user_stocks должна быть списком строк")

    return {
        "user_currencies": [currency.upper() for currency in currencies],
        "user_stocks": [stock.upper() for stock in stocks],
    }


def get_currency_rates(
    currencies: list[str],
    api_key: str | None = None,
) -> list[CurrencyRate]:
    """Получает стоимость иностранных валют в рублях."""

    if not currencies:
        return []

    key = api_key or os.getenv("CURRENCY_API_KEY")

    if not key:
        logger.error("Не задан ключ CURRENCY_API_KEY")
        return [{"currency": currency, "rate": 0.0} for currency in currencies]

    try:
        response = requests.get(
            CURRENCY_API_URL,
            headers={"apikey": key},
            params={
                "base_currency": "RUB",
                "currencies": ",".join(currencies),
            },
            timeout=API_TIMEOUT,
        )
        response.raise_for_status()
        response_data = response.json()
        rates_data = response_data["data"]
    except (
        requests.RequestException,
        KeyError,
        TypeError,
        ValueError,
    ) as error:
        logger.error("Ошибка получения курсов валют: %s", error)
        return [{"currency": currency, "rate": 0.0} for currency in currencies]

    result: list[CurrencyRate] = []

    for currency in currencies:
        try:
            currency_value = float(rates_data[currency]["value"])

            if currency_value <= 0:
                raise ValueError("Курс должен быть положительным")

            rate = round(1 / currency_value, 2)
        except (KeyError, TypeError, ValueError, ZeroDivisionError) as error:
            logger.error(
                "Не удалось обработать курс валюты %s: %s",
                currency,
                error,
            )
            rate = 0.0

        result.append(
            {
                "currency": currency,
                "rate": rate,
            }
        )

    return result


def get_stock_prices(
    stocks: list[str],
    api_key: str | None = None,
) -> list[StockPrice]:
    """Получает текущую стоимость акций."""

    if not stocks:
        return []

    key = api_key or os.getenv("STOCK_API_KEY")

    if not key:
        logger.error("Не задан ключ STOCK_API_KEY")
        return [{"stock": stock, "price": 0.0} for stock in stocks]

    result: list[StockPrice] = []

    for stock in stocks:
        try:
            response = requests.get(
                STOCK_API_URL,
                headers={"X-Finnhub-Token": key},
                params={"symbol": stock},
                timeout=API_TIMEOUT,
            )
            response.raise_for_status()
            price = float(response.json()["c"])

            if price <= 0:
                raise ValueError("Цена акции должна быть положительной")
        except (
            requests.RequestException,
            KeyError,
            TypeError,
            ValueError,
        ) as error:
            logger.error(
                "Не удалось получить стоимость акции %s: %s",
                stock,
                error,
            )
            price = 0.0

        result.append(
            {
                "stock": stock,
                "price": round(price, 2),
            }
        )

    return result
