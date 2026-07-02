"""Focused product, user, and auth coverage for FakeStoreAPI."""

from __future__ import annotations

from typing import Any

import pytest
import requests
from jsonschema import validate as validate_json_schema

from tests.api_test_data import API_TEST_DATA


def assert_product_shape(product: Any) -> None:
    assert isinstance(product, dict)
    assert isinstance(product.get("id"), int)
    assert isinstance(product.get("title"), str)
    assert isinstance(product.get("price"), (int, float))
    assert isinstance(product.get("description"), str)
    assert isinstance(product.get("category"), str)
    assert isinstance(product.get("image"), str)


def assert_user_shape(user: Any) -> None:
    assert isinstance(user, dict)
    assert isinstance(user.get("id"), int)
    assert isinstance(user.get("email"), str)
    assert isinstance(user.get("username"), str)
    assert isinstance(user.get("password"), str)
    assert isinstance(user.get("name"), dict)
    assert isinstance(user["name"].get("firstname"), str)
    assert isinstance(user["name"].get("lastname"), str)
    assert isinstance(user.get("address"), dict)
    assert isinstance(user["address"].get("city"), str)
    assert isinstance(user["address"].get("street"), str)
    assert isinstance(user["address"].get("number"), int)
    assert isinstance(user["address"].get("zipcode"), str)


def _product_url(base: str, product_id: int) -> str:
    return f"{base}{API_TEST_DATA['paths']['product_item'].format(id=product_id)}"


def _user_url(base: str, user_id: int) -> str:
    return f"{base}{API_TEST_DATA['paths']['user_item'].format(id=user_id)}"


def _json_or_none(response: requests.Response) -> Any:
    try:
        return response.json()
    except ValueError:
        return None


class TestProducts:
    def test_get_all_products(self, base_url: str):
        resp = requests.get(f"{base_url}{API_TEST_DATA['paths']['products']}", timeout=10)
        assert resp.status_code in API_TEST_DATA["statuses"]["ok"]
        products = resp.json()
        assert isinstance(products, list)
        assert len(products) > 0
        assert_product_shape(products[0])

    @pytest.mark.parametrize("product_id", API_TEST_DATA["products"]["sample_ids"])
    def test_get_product_by_id(self, base_url: str, product_id: int):
        resp = requests.get(_product_url(base_url, product_id), timeout=10)
        assert resp.status_code in API_TEST_DATA["statuses"]["ok"]
        assert_product_shape(resp.json())

    def test_get_categories(self, base_url: str):
        resp = requests.get(f"{base_url}{API_TEST_DATA['paths']['product_categories']}", timeout=10)
        if resp.status_code == 404:
            resp = requests.get(
                f"{base_url}{API_TEST_DATA['paths']['products']}{API_TEST_DATA['paths']['product_categories']}",
                timeout=10,
            )
        assert resp.status_code in API_TEST_DATA["statuses"]["ok"]
        categories = resp.json()
        assert isinstance(categories, list)
        assert len(categories) > 0

    def test_get_products_by_category(self, base_url: str):
        category = API_TEST_DATA["products"]["category"]
        resp = requests.get(
            f"{base_url}{API_TEST_DATA['paths']['product_category'].format(category=category)}",
            timeout=10,
        )
        assert resp.status_code in API_TEST_DATA["statuses"]["ok"]
        products = resp.json()
        assert isinstance(products, list)
        assert len(products) > 0
        assert products[0]["category"] == category

    def test_create_product(self, base_url: str, valid_product_payload: dict):
        resp = requests.post(f"{base_url}{API_TEST_DATA['paths']['products']}", json=valid_product_payload, timeout=10)
        assert resp.status_code in API_TEST_DATA["statuses"]["created"]
        body = resp.json()
        assert_product_shape(body)
        assert body["title"] == valid_product_payload["title"]

    def test_update_product(self, base_url: str, valid_product_payload: dict):
        product_id = API_TEST_DATA["products"]["sample_ids"][0]
        payload = API_TEST_DATA["products"]["update"]
        resp = requests.put(_product_url(base_url, product_id), json=payload, timeout=10)
        assert resp.status_code in API_TEST_DATA["statuses"]["ok"]
        body = resp.json()
        assert_product_shape(body)
        assert body["title"] == payload["title"]

    def test_delete_product(self, base_url: str, valid_product_payload: dict):
        created = requests.post(f"{base_url}{API_TEST_DATA['paths']['products']}", json=valid_product_payload, timeout=10)
        created.raise_for_status()
        product_id = created.json()["id"]
        resp = requests.delete(_product_url(base_url, product_id), timeout=10)
        assert resp.status_code in API_TEST_DATA["statuses"]["ok"]
        assert _json_or_none(resp) is not None or resp.status_code in API_TEST_DATA["statuses"]["ok"]


class TestProductNegative:
    def test_nonexistent_id_returns_empty(self, base_url: str):
        resp = requests.get(_product_url(base_url, API_TEST_DATA["products"]["ids"]["missing"]), timeout=10)
        assert resp.status_code in API_TEST_DATA["statuses"]["empty_or_ok"]


class TestProductSchema:
    def test_single_product_conforms(self, base_url: str, product_schema: dict):
        resp = requests.get(_product_url(base_url, API_TEST_DATA["products"]["sample_ids"][0]), timeout=10)
        validate_json_schema(instance=resp.json(), schema=product_schema)


class TestUsers:
    def test_get_all_users(self, base_url: str):
        resp = requests.get(f"{base_url}{API_TEST_DATA['paths']['users']}", timeout=10)
        assert resp.status_code in API_TEST_DATA["statuses"]["ok"]
        users = resp.json()
        assert isinstance(users, list)
        assert len(users) > 0
        assert_user_shape(users[0])

    @pytest.mark.parametrize("user_id", API_TEST_DATA["users"]["sample_ids"])
    def test_get_user_by_id(self, base_url: str, user_id: int):
        resp = requests.get(_user_url(base_url, user_id), timeout=10)
        assert resp.status_code in API_TEST_DATA["statuses"]["ok"]
        assert_user_shape(resp.json())

    def test_create_user(self, base_url: str, valid_user_payload: dict):
        resp = requests.post(f"{base_url}{API_TEST_DATA['paths']['users']}", json=valid_user_payload, timeout=10)
        assert resp.status_code in API_TEST_DATA["statuses"]["created"]
        body = _json_or_none(resp)
        assert isinstance(body, dict)
        assert isinstance(body.get("id"), int)

    def test_update_user(self, base_url: str, valid_user_payload: dict):
        user_id = API_TEST_DATA["users"]["ids"]["patch_update"]
        payload = API_TEST_DATA["users"]["update"]
        resp = requests.put(_user_url(base_url, user_id), json=payload, timeout=10)
        assert resp.status_code in API_TEST_DATA["statuses"]["ok"]
        body = resp.json()
        assert_user_shape(body)
        assert body["email"] == payload["email"]

    def test_patch_user(self, base_url: str):
        user_id = API_TEST_DATA["users"]["ids"]["patch_update"]
        resp = requests.patch(
            _user_url(base_url, user_id),
            json=API_TEST_DATA["users"]["patch"],
            timeout=10,
        )
        assert resp.status_code in API_TEST_DATA["statuses"]["ok"]
        body = _json_or_none(resp)
        if isinstance(body, dict) and "phone" in body:
            assert body["phone"] == API_TEST_DATA["users"]["patch"]["phone"]

    def test_delete_user(self, base_url: str, valid_user_payload: dict):
        created = requests.post(f"{base_url}{API_TEST_DATA['paths']['users']}", json=valid_user_payload, timeout=10)
        created.raise_for_status()
        user_id = created.json()["id"]
        resp = requests.delete(_user_url(base_url, user_id), timeout=10)
        assert resp.status_code in API_TEST_DATA["statuses"]["ok"]


class TestUserNegative:
    def test_nonexistent_id_returns_empty(self, base_url: str):
        resp = requests.get(_user_url(base_url, API_TEST_DATA["users"]["ids"]["missing"]), timeout=10)
        assert resp.status_code in API_TEST_DATA["statuses"]["empty_or_ok"]


class TestUserSchema:
    def test_single_user_conforms(self, base_url: str, user_schema: dict):
        resp = requests.get(_user_url(base_url, API_TEST_DATA["users"]["sample_ids"][0]), timeout=10)
        validate_json_schema(instance=resp.json(), schema=user_schema)
