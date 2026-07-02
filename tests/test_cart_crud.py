"""Cart CRUD test suite for FakeStoreAPI.

Coverage:
  - Positive CRUD for POST / GET / PUT / DELETE
  - Negative / edge cases
  - Authentication token flow
  - Response schema validation (JSON Schema)
  - Data-driven test (one scenario across 3+ product IDs)
  - Contract / snapshot test
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest
import requests
from jsonschema import validate as validate_json_schema

from tests.api_test_data import API_TEST_DATA


def assert_cart_shape(cart: Any) -> None:
    """Lightweight structural assertion every cart response must pass."""
    assert isinstance(cart, dict)
    assert isinstance(cart.get("id"), int)
    assert isinstance(cart.get("userId"), int)
    assert isinstance(cart.get("date"), str)
    assert isinstance(cart.get("products"), list)
    for item in cart["products"]:
        assert isinstance(item, dict)
        assert isinstance(item.get("productId"), int)
        assert isinstance(item.get("quantity"), int)
    if "__v" in cart:
        assert isinstance(cart["__v"], int)


def _cart_url(base: str, cart_id: int) -> str:
    return f"{base}{API_TEST_DATA['paths']['cart_item'].format(id=cart_id)}"


def _json_or_none(response: requests.Response) -> Any:
    try:
        return response.json()
    except ValueError:
        return None


def _type_schema(value: Any) -> dict[str, Any]:
    if isinstance(value, bool):
        return {"type": "boolean"}
    if isinstance(value, int):
        return {"type": "integer"}
    if isinstance(value, float):
        return {"type": "number"}
    if isinstance(value, str):
        return {"type": "string"}
    if value is None:
        return {"type": "null"}
    if isinstance(value, list):
        if not value:
            return {"type": "array"}
        return {"type": "array", "items": _type_schema(value[0])}
    if isinstance(value, dict):
        properties = {key: _type_schema(item) for key, item in value.items()}
        return {
            "type": "object",
            "required": sorted(properties.keys()),
            "properties": properties,
            "additionalProperties": False,
        }
    return {}


def _derive_contract_schema(instance: dict[str, Any]) -> dict[str, Any]:
    """Derive a JSON Schema from a live cart shape."""
    properties: dict[str, Any] = {}
    required: list[str] = []

    for key, value in instance.items():
        if key == "__v":
            properties[key] = {"type": "integer"}
            continue

        required.append(key)
        properties[key] = _type_schema(value)

    return {
        "$schema": "http://json-schema.org/draft-07/schema#",
        "title": "CartSnapshot",
        "type": "object",
        "required": sorted(required),
        "properties": properties,
        "additionalProperties": False,
    }


# ---------------------------------------------------------------------------
# 1. Positive cases
# ---------------------------------------------------------------------------


class TestCreateCart:
    def test_create_minimal(self, base_url: str):
        payload = API_TEST_DATA["cart"]["create_minimal"]
        resp = requests.post(f"{base_url}{API_TEST_DATA['paths']['carts']}", json=payload, timeout=10)
        assert resp.status_code in API_TEST_DATA["statuses"]["created"]
        body = resp.json()
        assert_cart_shape(body)
        assert body["userId"] == payload["userId"]
        assert body["products"] == payload["products"]

    def test_create_multiple_products(self, base_url: str, valid_cart_payload: dict):
        resp = requests.post(f"{base_url}{API_TEST_DATA['paths']['carts']}", json=valid_cart_payload, timeout=10)
        assert resp.status_code in API_TEST_DATA["statuses"]["created"]
        body = resp.json()
        assert_cart_shape(body)
        assert len(body["products"]) == len(valid_cart_payload["products"])


class TestGetCart:
    def test_get_existing(self, base_url: str):
        resp = requests.get(_cart_url(base_url, API_TEST_DATA["cart"]["ids"]["existing"][0]), timeout=10)
        assert resp.status_code in API_TEST_DATA["statuses"]["ok"]
        body = resp.json()
        assert_cart_shape(body)
        assert body["id"] == API_TEST_DATA["cart"]["ids"]["existing"][0]

class TestUpdateCart:
    def test_put_update(self, base_url: str, seeded_cart_id: int):
        payload = API_TEST_DATA["cart"]["update"]
        resp = requests.put(_cart_url(base_url, seeded_cart_id), json=payload, timeout=10)
        assert resp.status_code in API_TEST_DATA["statuses"]["ok"]
        body = resp.json()
        assert_cart_shape(body)
        assert body["userId"] == payload["userId"]
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
        body = resp.json()
        if body is not None:
            assert_cart_shape(body)
            assert body["id"] == fresh_cart_id

# ---------------------------------------------------------------------------
# 2. Negative / edge cases
# ---------------------------------------------------------------------------


class TestNegative:
    def test_get_nonexistent(self, base_url: str):
        resp = requests.get(_cart_url(base_url, API_TEST_DATA["cart"]["ids"]["missing"]), timeout=10)
        assert resp.status_code in API_TEST_DATA["statuses"]["empty_or_ok"]
        assert resp.json() is None

    def test_delete_nonexistent(self, base_url: str):
        resp = requests.delete(_cart_url(base_url, API_TEST_DATA["cart"]["ids"]["missing"]), timeout=10)
        assert resp.status_code in API_TEST_DATA["statuses"]["empty_or_ok"]
        assert resp.json() is None


# ---------------------------------------------------------------------------
# 3. Authentication
# ---------------------------------------------------------------------------


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
        resp = requests.get(_cart_url(base_url, API_TEST_DATA["cart"]["ids"]["existing"][0]), headers=auth_header, timeout=10)
        assert resp.status_code in API_TEST_DATA["statuses"]["ok"]
        assert_cart_shape(resp.json())


# ---------------------------------------------------------------------------
# 4. Response schema validation via JSON Schema
# ---------------------------------------------------------------------------


class TestSchema:
    def test_single_cart_conforms(self, base_url: str, cart_schema: dict):
        resp = requests.get(_cart_url(base_url, API_TEST_DATA["cart"]["ids"]["existing"][1]), timeout=10)
        validate_json_schema(instance=resp.json(), schema=cart_schema)

    def test_created_cart_conforms(self, base_url: str, cart_schema: dict):
        payload = API_TEST_DATA["cart"]["create_single_product"]
        payload = {
            "userId": payload["userId"],
            "date": payload["date"],
            "products": [{"productId": API_TEST_DATA["products"]["sample_ids"][1], "quantity": payload["quantity"]}],
        }
        resp = requests.post(f"{base_url}{API_TEST_DATA['paths']['carts']}", json=payload, timeout=10)
        validate_json_schema(instance=resp.json(), schema=cart_schema)


# ---------------------------------------------------------------------------
# 5. Data-driven test
# ---------------------------------------------------------------------------


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
        assert body["products"][0]["quantity"] == base_payload["quantity"]


# ---------------------------------------------------------------------------
# 6. Contract / snapshot test
# ---------------------------------------------------------------------------


class TestContractSnapshot:
    SNAPSHOT_PATH = "schemas/cart_snapshot.json"

    def test_record_and_enforce_snapshot(self, base_url: str):
        snapshot_file = Path(__file__).resolve().parent.parent / self.SNAPSHOT_PATH
        snapshot_file.parent.mkdir(parents=True, exist_ok=True)

        resp = requests.get(_cart_url(base_url, API_TEST_DATA["cart"]["ids"]["existing"][1]), timeout=10)
        resp.raise_for_status()
        live_cart = resp.json()
        assert isinstance(live_cart, dict)

        if not snapshot_file.exists():
            schema = _derive_contract_schema(live_cart)
            snapshot_file.write_text(json.dumps(schema, indent=2))
            pytest.skip("Snapshot created - re-run to enforce.")

        stored = json.loads(snapshot_file.read_text())
        validate_json_schema(instance=live_cart, schema=stored)

        resp = requests.get(_cart_url(base_url, API_TEST_DATA["cart"]["ids"]["existing"][2]), timeout=10)
        validate_json_schema(instance=resp.json(), schema=stored)
