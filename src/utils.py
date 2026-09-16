import logging
from pathlib import Path

import pandas as pd

logger = logging.getLogger(__name__)

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_OPERATIONS_PATH = PROJECT_ROOT / "data" / "operations.xlsx"

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
