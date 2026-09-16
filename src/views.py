import json
import logging
from datetime import datetime
from typing import TypedDict

import pandas as pd

from src.utils import (
    CurrencyRate,
    StockPrice,
    get_currency_rates,
    get_stock_prices,
    load_transactions,
    load_user_settings,
)

logger = logging.getLogger(__name__)


class CardInfo(TypedDict):
    """Структура информации о расходах по карте."""

    last_digits: str
    total_spent: float
    cashback: float


class TransactionInfo(TypedDict):
    """Структура информации о транзакции."""

    date: str
    amount: float
    category: str
    description: str


class MainPageResponse(TypedDict):
    """Структура ответа страницы «Главная»."""

    greeting: str
    cards: list[CardInfo]
    top_transactions: list[TransactionInfo]
    currency_rates: list[CurrencyRate]
    stock_prices: list[StockPrice]


def get_greeting(current_datetime: datetime) -> str:
    """Возвращает приветствие в зависимости от времени суток."""

    hour = current_datetime.hour

    if 6 <= hour < 12:
        return "Доброе утро"
    if 12 <= hour < 18:
        return "Добрый день"
    if 18 <= hour < 23:
        return "Добрый вечер"

    return "Доброй ночи"


def filter_transactions_by_month(
    transactions: pd.DataFrame,
    end_datetime: datetime,
) -> pd.DataFrame:
    """Возвращает транзакции с начала месяца по указанную дату и время."""

    start_datetime = end_datetime.replace(
        day=1,
        hour=0,
        minute=0,
        second=0,
        microsecond=0,
    )

    operation_dates = pd.to_datetime(
        transactions["Дата операции"],
        dayfirst=True,
        errors="coerce",
    )

    date_mask = operation_dates.between(
        start_datetime,
        end_datetime,
        inclusive="both",
    )

    filtered_transactions = transactions.loc[date_mask].copy()

    logger.info(
        "Отобрано транзакций за период %s — %s: %s",
        start_datetime,
        end_datetime,
        len(filtered_transactions),
    )
    return filtered_transactions


def get_cards_info(transactions: pd.DataFrame) -> list[CardInfo]:
    """Возвращает суммы расходов и кешбэк по каждой карте."""

    expenses = transactions.loc[
        (transactions["Статус"] == "OK") & transactions["Номер карты"].notna() & (transactions["Сумма платежа"] < 0),
        ["Номер карты", "Сумма платежа"],
    ].copy()

    if expenses.empty:
        return []

    expenses["Сумма платежа"] = expenses["Сумма платежа"].abs()

    expenses_by_card = (
        expenses.groupby("Номер карты", as_index=False)
        .agg(total_spent=("Сумма платежа", "sum"))
        .sort_values(by="Номер карты")
    )

    cards: list[CardInfo] = []

    for _, row in expenses_by_card.iterrows():
        total_spent = round(float(row["total_spent"]), 2)

        cards.append(
            {
                "last_digits": str(row["Номер карты"])[-4:],
                "total_spent": total_spent,
                "cashback": round(total_spent / 100, 2),
            }
        )

    logger.info("Сформирована информация по картам: %s", len(cards))
    return cards


def get_top_transactions(
    transactions: pd.DataFrame,
    limit: int = 5,
) -> list[TransactionInfo]:
    """Возвращает крупнейшие успешные транзакции по сумме платежа."""

    if limit <= 0:
        return []

    completed_transactions = transactions.loc[
        (transactions["Статус"] == "OK") & transactions["Сумма платежа"].notna(),
        [
            "Дата операции",
            "Сумма платежа",
            "Категория",
            "Описание",
        ],
    ].copy()

    completed_transactions["Дата операции"] = pd.to_datetime(
        completed_transactions["Дата операции"],
        dayfirst=True,
        errors="coerce",
    )
    completed_transactions = completed_transactions.dropna(subset=["Дата операции"])

    completed_transactions["amount"] = completed_transactions["Сумма платежа"].abs()

    top_transactions = completed_transactions.nlargest(limit, "amount")

    result: list[TransactionInfo] = []

    for _, row in top_transactions.iterrows():
        operation_date = pd.Timestamp(row["Дата операции"])

        result.append(
            {
                "date": operation_date.strftime("%d.%m.%Y"),
                "amount": round(float(row["amount"]), 2),
                "category": str(row["Категория"]),
                "description": str(row["Описание"]),
            }
        )

    logger.info("Сформирован топ транзакций: %s", len(result))
    return result


def main_page(date_time: str) -> str:
    """Формирует JSON-ответ для страницы «Главная»."""

    try:
        current_datetime = datetime.strptime(
            date_time,
            "%Y-%m-%d %H:%M:%S",
        )
    except ValueError as error:
        logger.error("Получена некорректная дата: %s", date_time)
        raise ValueError("Дата должна быть в формате YYYY-MM-DD HH:MM:SS") from error

    transactions = load_transactions()
    settings = load_user_settings()

    month_transactions = filter_transactions_by_month(
        transactions,
        current_datetime,
    )

    response: MainPageResponse = {
        "greeting": get_greeting(current_datetime),
        "cards": get_cards_info(month_transactions),
        "top_transactions": get_top_transactions(month_transactions),
        "currency_rates": get_currency_rates(settings["user_currencies"]),
        "stock_prices": get_stock_prices(settings["user_stocks"]),
    }

    logger.info("Сформирован ответ страницы «Главная»")
    return json.dumps(response, ensure_ascii=False, indent=2)
