import json
from pathlib import Path

import pandas as pd
import pytest

from src.reports import save_report, spending_by_category


def test_spending_by_category(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Проверяет фильтрацию расходов по категории и трехмесячному периоду."""

    transactions = pd.DataFrame(
        {
            "Дата операции": [
                "29.09.2021 12:00:00",
                "30.09.2021 00:00:00",
                "31.12.2021 23:59:59",
                "01.01.2022 00:00:00",
                "15.11.2021 12:00:00",
                "16.11.2021 12:00:00",
                "17.11.2021 12:00:00",
            ],
            "Категория": [
                "Супермаркеты",
                "Супермаркеты",
                "Супермаркеты",
                "Супермаркеты",
                "Транспорт",
                "Супермаркеты",
                "Супермаркеты",
            ],
            "Статус": [
                "OK",
                "OK",
                "OK",
                "OK",
                "OK",
                "FAILED",
                "OK",
            ],
            "Сумма платежа": [
                -100.0,
                -200.0,
                -300.0,
                -400.0,
                -500.0,
                -600.0,
                700.0,
            ],
            "Описание": [
                "Раньше периода",
                "Начало периода",
                "Конец периода",
                "Позже периода",
                "Другая категория",
                "Неуспешная операция",
                "Поступление",
            ],
        }
    )
    report_path = tmp_path / "report.json"
    monkeypatch.setattr(
        "src.reports.DEFAULT_REPORT_PATH",
        report_path,
    )

    result = spending_by_category(
        transactions,
        "Супермаркеты",
        "2021-12-31",
    )

    assert result["Описание"].tolist() == [
        "Начало периода",
        "Конец периода",
    ]
    assert result["Сумма платежа"].tolist() == [
        -200.0,
        -300.0,
    ]
    assert report_path.is_file()

    saved_report = json.loads(report_path.read_text(encoding="utf-8"))
    assert [transaction["Описание"] for transaction in saved_report] == [
        "Начало периода",
        "Конец периода",
    ]


def test_spending_by_category_with_current_date(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Проверяет формирование отчета без явно переданной даты."""

    current_date = pd.Timestamp.now().normalize()
    transactions = pd.DataFrame(
        {
            "Дата операции": [
                current_date,
                current_date - pd.DateOffset(months=4),
            ],
            "Категория": [
                "Супермаркеты",
                "Супермаркеты",
            ],
            "Статус": [
                "OK",
                "OK",
            ],
            "Сумма платежа": [
                -100.0,
                -200.0,
            ],
            "Описание": [
                "Сегодня",
                "Раньше периода",
            ],
        }
    )
    monkeypatch.setattr(
        "src.reports.DEFAULT_REPORT_PATH",
        tmp_path / "report.json",
    )

    result = spending_by_category(
        transactions,
        "Супермаркеты",
    )

    assert result["Описание"].tolist() == ["Сегодня"]


def test_spending_by_category_with_invalid_date() -> None:
    """Проверяет обработку некорректной даты."""

    with pytest.raises(
        ValueError,
        match="Получена некорректная дата",
    ):
        spending_by_category(
            pd.DataFrame(),
            "Супермаркеты",
            "некорректная дата",
        )


def test_save_report_with_custom_file_name(
    tmp_path: Path,
) -> None:
    """Проверяет декоратор с пользовательским именем файла."""

    report_path = tmp_path / "custom_report.json"

    @save_report(report_path)
    def create_report(value: int) -> pd.DataFrame:
        return pd.DataFrame(
            [
                {
                    "value": value,
                }
            ]
        )

    result = create_report(42)

    assert result.to_dict(orient="records") == [{"value": 42}]
    assert report_path.is_file()
    assert json.loads(report_path.read_text(encoding="utf-8")) == [{"value": 42}]
