import json

import pandas as pd
import pytest

from src.services import simple_search


@pytest.fixture
def search_transactions() -> pd.DataFrame:
    """Возвращает транзакции для тестирования поиска."""

    return pd.DataFrame(
        [
            {
                "Дата операции": pd.Timestamp("2021-01-01 10:00:00"),
                "Категория": "Супермаркеты",
                "Описание": "Магнит",
            },
            {
                "Дата операции": pd.Timestamp("2021-01-02 11:00:00"),
                "Категория": "Переводы",
                "Описание": "Иван П.",
            },
            {
                "Дата операции": pd.Timestamp("2021-01-03 12:00:00"),
                "Категория": "Транспорт",
                "Описание": "Яндекс Go",
            },
            {
                "Дата операции": pd.Timestamp("2021-01-04 13:00:00"),
                "Категория": None,
                "Описание": "Магазин Магнит",
            },
            {
                "Дата операции": pd.Timestamp("2021-01-05 14:00:00"),
                "Категория": "Аптеки",
                "Описание": None,
            },
        ]
    )


@pytest.mark.parametrize(
    ("query", "expected_descriptions"),
    [
        ("маГн", ["Магнит", "Магазин Магнит"]),
        ("ПЕРЕ", ["Иван П."]),
        ("яндекс", ["Яндекс Go"]),
    ],
)
def test_simple_search(
    search_transactions: pd.DataFrame,
    query: str,
    expected_descriptions: list[str],
) -> None:
    """Проверяет поиск по подстроке без учета регистра."""

    result = json.loads(simple_search(search_transactions, query))

    assert [transaction["Описание"] for transaction in result] == expected_descriptions


@pytest.mark.parametrize("query", ["", "   "])
def test_simple_search_empty_query(
    search_transactions: pd.DataFrame,
    query: str,
) -> None:
    """Проверяет поиск с пустым запросом."""

    assert json.loads(simple_search(search_transactions, query)) == []


def test_simple_search_without_matches(
    search_transactions: pd.DataFrame,
) -> None:
    """Проверяет результат при отсутствии совпадений."""

    assert json.loads(simple_search(search_transactions, "кинотеатр")) == []


def test_simple_search_serialization(
    search_transactions: pd.DataFrame,
) -> None:
    """Проверяет сериализацию даты и отсутствующего описания."""

    result = json.loads(simple_search(search_transactions, "апте"))

    assert result[0]["Описание"] is None
    assert result[0]["Дата операции"] == ("2021-01-05T14:00:00.000")
