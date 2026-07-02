# FakeStoreAPI Backend Automation

Lean API test suite for FakeStoreAPI covering the core assignment requirements for `products`, `carts`, `users`, and `auth`.

## Framework Choice

### `pytest`
Chosen because it keeps API tests compact and readable while still supporting the features this assignment needs:
- fixtures for shared setup like base URL, auth token, and seeded data
- parametrization for data-driven coverage
- simple test collection and selection
- clear assertion failures
- lightweight structure for both functional and contract-style checks

### `requests`
Used for direct HTTP calls to the live API.
- simple and explicit
- no extra abstraction layer
- good fit for validating actual request/response behavior

### `jsonschema`
Used for response validation.
- checks response shape without overfitting to exact values
- useful for contract tests and regression detection
- works well for reusable schema files

### Why this stack
The goal is to verify a public API directly, not to build a full testing framework. `pytest + requests + jsonschema` gives the right balance of:
- speed of implementation
- clarity of assertions
- reusable test data
- maintainability for a small-to-medium API suite

This repository is intentionally lean:
- it keeps only representative tests that prove each required behavior
- it avoids redundant permutations that do not add much assignment value
- it stays simple enough to explain clearly during review

## How the suite is organized

- `tests/test_cart_crud.py`
  - essential cart CRUD
  - cart auth checks
  - cart schema validation
  - cart data-driven test
  - cart contract snapshot bootstrap and enforcement
- `tests/test_products_users_auth.py`
  - representative product coverage
  - representative user coverage
- `tests/conftest.py`
  - shared fixtures
  - logging
  - base URL and auth token handling
- `test_data/fakestore.json`
  - shared test inputs and endpoint paths

## Extension Plan

### Parallelisation
If the suite grows or runtime becomes a problem, the next step is parallel execution with `pytest-xdist`.

Practical plan:
- mark tests by resource type: `cart`, `product`, `user`, `auth`, `schema`
- separate smoke tests from broader regression tests
- run independent read-only tests in parallel
- keep write tests grouped if the target API has rate limits or shared-state concerns

Recommended command:
```bash
pytest -n auto
```

If the API is unstable under concurrent writes, keep the write paths serial and only parallelise read-only tests.

### Reporting
For reporting, the next useful layers are:
- `pytest-html` for a quick shareable HTML report
- JUnit XML output for CI
- Allure if richer dashboards and history are needed

Practical plan:
- keep terminal logs for local debugging
- generate `junit.xml` in CI
- attach request/response logs to failed tests
- publish HTML or Allure reports as build artifacts
- keep the current suite lean unless a rubric explicitly asks for more breadth

Example CI-friendly output:
```bash
pytest --junitxml=reports/junit.xml
```

## Configuration

The base API URL can be overridden with:

```bash
FAKESTOREAPI_BASE_URL=https://fakestoreapi.com
```

If unset, the suite defaults to the public FakeStoreAPI host.
