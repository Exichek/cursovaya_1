import logging

from src.views import main_page

DEFAULT_DATE_TIME = "2021-12-31 23:59:59"


def main(date_time: str = DEFAULT_DATE_TIME) -> None:
    """Запускает формирование данных для страницы «Главная»."""

    logging.basicConfig(
        level=logging.INFO,
        format=("%(asctime)s - %(name)s - " "%(levelname)s - %(message)s"),
    )

    print(main_page(date_time))


if __name__ == "__main__":  # pragma: no cover
    main()
