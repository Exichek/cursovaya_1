# Курсовая работа №1

Приложение для анализа банковских транзакций из Excel-файла. Проект формирует данные для страницы «Главная», выполняет поиск по операциям и создает отчеты по расходам.

## Реализованные возможности

### Страница «Главная»

Функция `main_page` принимает дату и время в формате `YYYY-MM-DD HH:MM:SS` и возвращает JSON-ответ со следующими данными:

- приветствие в зависимости от времени суток;
- расходы и кэшбэк по каждой карте;
- пять крупнейших транзакций;
- курсы выбранных валют;
- стоимость выбранных акций.

Для расчетов используются транзакции от начала месяца до переданной даты.

### Простой поиск

Функция `simple_search` выполняет регистронезависимый поиск по:

- категории транзакции;
- описанию транзакции.

Результат возвращается в формате JSON.

### Отчет по тратам по категории

Функция `spending_by_category` возвращает расходы по заданной категории за последние три месяца от переданной даты.

Результат работы отчета автоматически сохраняется декоратором в JSON-файл:

```text
reports/report.json
```

Можно указать собственный путь для сохранения отчета.

### Работа со сторонними API

Приложение получает:

- курсы валют через CurrencyAPI;
- стоимость акций через Finnhub API.

При недоступности API или отсутствии ключа для соответствующих значений возвращается `0.0`, а ошибка записывается в журнал.

## Структура проекта

```text
cursovaya_1/
├── data/
│   └── operations.xlsx
├── src/
│   ├── __init__.py
│   ├── main.py
│   ├── reports.py
│   ├── services.py
│   ├── utils.py
│   └── views.py
├── tests/
│   ├── conftest.py
│   ├── test_main.py
│   ├── test_reports.py
│   ├── test_services.py
│   ├── test_utils.py
│   └── test_views.py
├── .env.example
├── .flake8
├── .gitignore
├── pyproject.toml
├── poetry.lock
├── README.md
└── user_settings.json
```

Основные модули:

- `src/utils.py` — загрузка и проверка транзакций, чтение настроек, работа с API;
- `src/views.py` — формирование JSON-ответа страницы «Главная»;
- `src/services.py` — сервис простого поиска по транзакциям;
- `src/reports.py` — отчет по категории и декоратор сохранения результатов;
- `src/main.py` — точка входа в приложение;
- `tests/` — модульные тесты проекта.

## Требования

- Python `3.14`;
- Poetry `2.0` или новее.

## Установка

Клонируйте репозиторий:

```powershell
git clone https://github.com/Exichek/cursovaya_1.git
cd cursovaya_1
```

Установите зависимости:

```powershell
poetry install
```

Создайте файл с переменными окружения на основе примера:

```powershell
Copy-Item .env.example .env
```

Заполните API-ключи в файле `.env`:

```dotenv
CURRENCY_API_KEY=ваш_ключ_currencyapi
STOCK_API_KEY=ваш_ключ_finnhub
```

Файл `.env` содержит секретные данные и не отслеживается Git.

## Пользовательские настройки

Список валют и акций настраивается в файле `user_settings.json`:

```json
{
  "user_currencies": [
    "USD",
    "EUR"
  ],
  "user_stocks": [
    "AAPL",
    "AMZN",
    "GOOGL",
    "MSFT",
    "TSLA"
  ]
}
```

## Запуск приложения

Запустите приложение командой:

```powershell
poetry run python -m src.main
```

В консоль будет выведен JSON-ответ страницы «Главная».

## Запуск тестов

```powershell
poetry run pytest
```

Тесты запускаются с измерением покрытия кода. Текущее покрытие проекта составляет `100%`.

## Проверка качества кода

Проверка форматирования Black:

```powershell
poetry run black --check src tests
```

Проверка сортировки импортов:

```powershell
poetry run isort --check-only src tests
```

Проверка соответствия Flake8:

```powershell
poetry run flake8 src tests
```

Проверка статической типизации:

```powershell
poetry run mypy src tests
```

## Используемые технологии

- Python;
- pandas;
- openpyxl;
- Requests;
- python-dotenv;
- pytest;
- pytest-cov;
- Black;
- isort;
- Flake8;
- mypy.
