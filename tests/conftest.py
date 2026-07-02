from __future__ import annotations

import logging
import json
import os
from pathlib import Path
from typing import Any

import pytest
import requests

from tests.api_test_data import API_TEST_DATA

BASE_URL = os.getenv("FAKESTOREAPI_BASE_URL", "https://fakestoreapi.com")
LOGGER = logging.getLogger("shopflo.tests")


def pytest_configure(config: pytest.Config) -> None:
    if not logging.getLogger().handlers:
        logging.basicConfig(
            level=logging.INFO,
            format="%(asctime)s %(levelname)s %(name)s - %(message)s",
        )
    logging.getLogger("urllib3").setLevel(logging.WARNING)


@pytest.fixture(autouse=True)
def log_http_requests(monkeypatch: pytest.MonkeyPatch):
    original_request = requests.sessions.Session.request

    def logged_request(
        self: requests.Session,
        method: str,
        url: str,
        *args: Any,
        **kwargs: Any,
    ):
        LOGGER.info("HTTP %s %s", method.upper(), url)
        if kwargs.get("json") is not None:
            LOGGER.info("Request JSON: %s", kwargs["json"])
        if kwargs.get("params") is not None:
            LOGGER.info("Request params: %s", kwargs["params"])

        response = original_request(self, method, url, *args, **kwargs)

        try:
            response_body = response.json()
        except ValueError:
            response_body = response.text[:500]

        LOGGER.info("Response %s %s", response.status_code, response_body)
        return response

    monkeypatch.setattr(requests.sessions.Session, "request", logged_request)
    yield


@pytest.fixture(scope="session")
def base_url() -> str:
    return BASE_URL


@pytest.fixture(scope="session")
def auth_token(base_url: str) -> str:
    resp = requests.post(
        f"{base_url}{API_TEST_DATA['paths']['auth_login']}",
        json=API_TEST_DATA["auth"]["valid"],
        timeout=10,
    )
    resp.raise_for_status()
    token = resp.json()["token"]
    assert isinstance(token, str)
    return token


@pytest.fixture
def auth_header(auth_token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {auth_token}"}


@pytest.fixture(scope="session")
def cart_schema() -> dict:
    schema_path = Path(__file__).resolve().parent.parent / "schemas" / "cart_schema.json"
    return json.loads(schema_path.read_text())


@pytest.fixture(scope="session")
def product_schema() -> dict:
    schema_path = Path(__file__).resolve().parent.parent / "schemas" / "product_schema.json"
    return json.loads(schema_path.read_text())


@pytest.fixture(scope="session")
def user_schema() -> dict:
    schema_path = Path(__file__).resolve().parent.parent / "schemas" / "user_schema.json"
    return json.loads(schema_path.read_text())


@pytest.fixture
def valid_cart_payload() -> dict:
    return API_TEST_DATA["cart"]["create_multiple"]


@pytest.fixture
def valid_product_payload() -> dict:
    return API_TEST_DATA["products"]["create"]


@pytest.fixture
def valid_user_payload() -> dict:
    return API_TEST_DATA["users"]["create"]


@pytest.fixture
def seeded_cart_id(base_url: str) -> int:
    resp = requests.post(
        f"{base_url}{API_TEST_DATA['paths']['carts']}",
        json=API_TEST_DATA["cart"]["seed"],
        timeout=10,
    )
    resp.raise_for_status()
    cart_id = resp.json()["id"]
    yield cart_id
    requests.delete(f"{base_url}{API_TEST_DATA['paths']['cart_item'].format(id=cart_id)}", timeout=10)
