from unittest.mock import Mock

import pytest

import src.main as main_module


def test_main(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Проверяет запуск главной функции приложения."""

    response = '{"greeting": "Доброй ночи"}'
    main_page_mock = Mock(return_value=response)

    monkeypatch.setattr(
        main_module,
        "main_page",
        main_page_mock,
    )

    main_module.main("2021-12-31 23:59:59")

    assert capsys.readouterr().out.strip() == response
    main_page_mock.assert_called_once_with("2021-12-31 23:59:59")
