from __future__ import annotations

from django.test import override_settings


def test_get_config_returns_settings_dict() -> None:
    from django_poli_page.conf import get_config

    with override_settings(POLI_PAGE={"API_KEY": "pp_test_x", "TIMEOUT": 45.0}):
        cfg = get_config()
    assert cfg["API_KEY"] == "pp_test_x"
    assert cfg["TIMEOUT"] == 45.0


def test_get_config_empty_dict_when_setting_unset() -> None:
    from django_poli_page.conf import get_config

    with override_settings(POLI_PAGE={}):
        cfg = get_config()
    assert cfg == {}
