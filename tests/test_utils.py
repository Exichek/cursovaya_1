from pathlib import Path

import pandas as pd
import pytest

from src.utils import load_transactions


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
