"""Focused cart CRUD coverage for FakeStoreAPI."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest
import requests
from jsonschema import validate as validate_json_schema

from tests.api_test_data import API_TEST_DATA


def assert_cart_shape(cart: Any) -> None:
    assert isinstance(cart, dict)
    assert isinstance(cart.get("id"), int)
    assert isinstance(cart.get("userId"), int)
    assert isinstance(cart.get("date"), str)
    assert isinstance(cart.get("products"), list)
    for item in cart["products"]:
        assert isinstance(item, dict)
        assert isinstance(item.get("productId"), int)
        assert isinstance(item.get("quantity"), int)


def _cart_url(base: str, cart_id: int) -> str:
    return f"{base}{API_TEST_DATA['paths']['cart_item'].format(id=cart_id)}"


def _json_or_none(response: requests.Response) -> Any:
    try:
        return response.json()
    except ValueError:
        return None


class TestCreateCart:
    def test_create_minimal(self, base_url: str):
        payload = API_TEST_DATA["cart"]["create_minimal"]
        resp = requests.post(f"{base_url}{API_TEST_DATA['paths']['carts']}", json=payload, timeout=10)
        assert resp.status_code in API_TEST_DATA["statuses"]["created"]
        body = resp.json()
        assert_cart_shape(body)
        assert body["userId"] == payload["userId"]


class TestGetCart:
    def test_get_existing(self, base_url: str):
        cart_id = API_TEST_DATA["cart"]["ids"]["existing"][0]
        resp = requests.get(_cart_url(base_url, cart_id), timeout=10)
        assert resp.status_code in API_TEST_DATA["statuses"]["ok"]
        body = resp.json()
        assert_cart_shape(body)
        assert body["id"] == cart_id


class TestUpdateCart:
    def test_put_update(self, base_url: str, seeded_cart_id: int):
        payload = API_TEST_DATA["cart"]["update"]
        resp = requests.put(_cart_url(base_url, seeded_cart_id), json=payload, timeout=10)
        assert resp.status_code in API_TEST_DATA["statuses"]["ok"]
        body = resp.json()
        assert_cart_shape(body)
        assert body["products"] == payload["products"]


class TestDeleteCart:
    @pytest.fixture
    def fresh_cart_id(self, base_url: str) -> int:
        resp = requests.post(
            f"{base_url}{API_TEST_DATA['paths']['carts']}",
            json=API_TEST_DATA["cart"]["seed"],
            timeout=10,
        )
        resp.raise_for_status()
        cart_id = resp.json()["id"]
        yield cart_id
        requests.delete(_cart_url(base_url, cart_id), timeout=10)

    def test_delete_existing(self, base_url: str, fresh_cart_id: int):
        resp = requests.delete(_cart_url(base_url, fresh_cart_id), timeout=10)
        assert resp.status_code in API_TEST_DATA["statuses"]["ok"]
        body = _json_or_none(resp)
        if isinstance(body, dict):
            assert body["id"] == fresh_cart_id


class TestNegative:
    def test_get_nonexistent(self, base_url: str):
        resp = requests.get(_cart_url(base_url, API_TEST_DATA["cart"]["ids"]["missing"]), timeout=10)
        assert resp.status_code in API_TEST_DATA["statuses"]["empty_or_ok"]
        assert resp.json() is None

    def test_delete_nonexistent(self, base_url: str):
        resp = requests.delete(_cart_url(base_url, API_TEST_DATA["cart"]["ids"]["missing"]), timeout=10)
        assert resp.status_code in API_TEST_DATA["statuses"]["empty_or_ok"]
        assert resp.json() is None


class TestAuth:
    def test_obtain_token(self, auth_token: str):
        assert isinstance(auth_token, str)
        assert len(auth_token) > 20

    def test_invalid_login_rejected(self, base_url: str):
        resp = requests.post(
            f"{base_url}{API_TEST_DATA['paths']['auth_login']}",
            json=API_TEST_DATA["auth"]["invalid"],
            timeout=10,
        )
        assert resp.status_code in API_TEST_DATA["statuses"]["write_rejected"]

    def test_authenticated_request_succeeds(self, base_url: str, auth_header: dict):
        cart_id = API_TEST_DATA["cart"]["ids"]["existing"][0]
        resp = requests.get(_cart_url(base_url, cart_id), headers=auth_header, timeout=10)
        assert resp.status_code in API_TEST_DATA["statuses"]["ok"]
        assert_cart_shape(resp.json())


class TestSchema:
    def test_single_cart_conforms(self, base_url: str, cart_schema: dict):
        cart_id = API_TEST_DATA["cart"]["ids"]["existing"][1]
        resp = requests.get(_cart_url(base_url, cart_id), timeout=10)
        validate_json_schema(instance=resp.json(), schema=cart_schema)

    def test_created_cart_conforms(self, base_url: str, cart_schema: dict):
        payload = {
            "userId": API_TEST_DATA["cart"]["create_single_product"]["userId"],
            "date": API_TEST_DATA["cart"]["create_single_product"]["date"],
            "products": [
                {
                    "productId": API_TEST_DATA["products"]["sample_ids"][1],
                    "quantity": API_TEST_DATA["cart"]["create_single_product"]["quantity"],
                }
            ],
        }
        resp = requests.post(f"{base_url}{API_TEST_DATA['paths']['carts']}", json=payload, timeout=10)
        validate_json_schema(instance=resp.json(), schema=cart_schema)


class TestDataDriven:
    @pytest.mark.parametrize("product_id", API_TEST_DATA["cart"]["ids"]["data_driven_product_ids"])
    def test_create_cart_single_product(self, base_url: str, product_id: int):
        base_payload = API_TEST_DATA["cart"]["create_single_product"]
        payload = {
            "userId": base_payload["userId"],
            "date": base_payload["date"],
            "products": [{"productId": product_id, "quantity": base_payload["quantity"]}],
        }
        resp = requests.post(f"{base_url}{API_TEST_DATA['paths']['carts']}", json=payload, timeout=10)
        assert resp.status_code in API_TEST_DATA["statuses"]["created"]
        body = resp.json()
        assert_cart_shape(body)
        assert len(body["products"]) == 1
        assert body["products"][0]["productId"] == product_id


class TestContractSnapshot:
    SNAPSHOT_PATH = "schemas/cart_snapshot.json"

    def test_record_and_enforce_snapshot(self, base_url: str):
        snapshot_file = Path(__file__).resolve().parent.parent / self.SNAPSHOT_PATH
        snapshot_file.parent.mkdir(parents=True, exist_ok=True)

        cart_id = API_TEST_DATA["cart"]["ids"]["existing"][1]
        resp = requests.get(_cart_url(base_url, cart_id), timeout=10)
        resp.raise_for_status()
        live_cart = resp.json()

        if not snapshot_file.exists():
            snapshot_file.write_text(json.dumps(live_cart, indent=2))
            pytest.skip("Snapshot created - re-run to enforce.")

        stored = json.loads(snapshot_file.read_text())
        assert live_cart.keys() == stored.keys()
        assert set(live_cart["products"][0].keys()) == set(stored["products"][0].keys())
