import json
import logging
from typing import cast

import pandas as pd

logger = logging.getLogger(__name__)


def _matches_query(
    transaction: dict[str, object],
    query: str,
) -> bool:
    """Проверяет наличие запроса в категории или описании транзакции."""

    category = str(transaction.get("Категория") or "").casefold()
    description = str(transaction.get("Описание") or "").casefold()

    return query in category or query in description


def simple_search(
    transactions: pd.DataFrame,
    query: str,
) -> str:
    """Возвращает JSON с транзакциями, содержащими поисковый запрос."""

    normalized_query = query.strip().casefold()

    if not normalized_query:
        logger.info("Получен пустой поисковый запрос")
        return "[]"

    records_json = cast(
        str,
        transactions.to_json(
            orient="records",
            force_ascii=False,
            date_format="iso",
        ),
    )
    records: list[dict[str, object]] = json.loads(records_json)

    found_transactions = list(
        filter(
            lambda transaction: _matches_query(
                transaction,
                normalized_query,
            ),
            records,
        )
    )

    logger.info("Найдено транзакций: %s", len(found_transactions))
    return json.dumps(
        found_transactions,
        ensure_ascii=False,
        indent=2,
    )
