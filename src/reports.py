import logging
from collections.abc import Callable
from functools import wraps
from pathlib import Path
from typing import ParamSpec

import pandas as pd

from src.utils import PROJECT_ROOT

logger = logging.getLogger(__name__)

DEFAULT_REPORT_PATH = PROJECT_ROOT / "reports" / "report.json"

P = ParamSpec("P")


def save_report(
    file_name: str | Path | None = None,
) -> Callable[
    [Callable[P, pd.DataFrame]],
    Callable[P, pd.DataFrame],
]:
    """Создает декоратор, записывающий результат отчета в JSON-файл."""

    def decorator(
        function: Callable[P, pd.DataFrame],
    ) -> Callable[P, pd.DataFrame]:
        @wraps(function)
        def wrapper(
            *args: P.args,
            **kwargs: P.kwargs,
        ) -> pd.DataFrame:
            result = function(*args, **kwargs)

            output_path = Path(file_name) if file_name is not None else DEFAULT_REPORT_PATH
            output_path.parent.mkdir(
                parents=True,
                exist_ok=True,
            )
            result.to_json(
                output_path,
                orient="records",
                force_ascii=False,
                date_format="iso",
                indent=2,
            )

            logger.info(
                "Отчет записан в файл: %s",
                output_path,
            )
            return result

        return wrapper

    return decorator


@save_report()
def spending_by_category(
    transactions: pd.DataFrame,
    category: str,
    date: str | None = None,
) -> pd.DataFrame:
    """Возвращает расходы заданной категории за последние три месяца."""

    if date is None:
        end_date = pd.Timestamp.now().normalize()
    else:
        parsed_date = pd.to_datetime(
            date,
            errors="coerce",
        )

        if pd.isna(parsed_date):
            raise ValueError("Получена некорректная дата")

        end_date = pd.Timestamp(parsed_date).normalize()

    start_date = end_date - pd.DateOffset(months=3)

    operation_dates = pd.to_datetime(
        transactions["Дата операции"],
        dayfirst=True,
        errors="coerce",
    ).dt.normalize()

    date_mask = operation_dates.between(
        start_date,
        end_date,
        inclusive="both",
    )
    category_mask = transactions["Категория"] == category
    status_mask = transactions["Статус"] == "OK"
    expense_mask = transactions["Сумма платежа"] < 0

    result = transactions.loc[date_mask & category_mask & status_mask & expense_mask].copy()

    logger.info(
        "Сформирован отчет по категории «%s»: %s транзакций",
        category,
        len(result),
    )
    return result.reset_index(drop=True)
