#!/usr/bin/env bash
# Builds a small Python repo whose suite holds three bad tests and one good test.
set -euo pipefail
mkdir -p app tests
touch app/__init__.py tests/__init__.py
cat > app/price.py <<'PY'
BULK_THRESHOLD = 10
BULK_DISCOUNT = 0.1


def line_total(unit_price: float, quantity: int) -> float:
    total = unit_price * quantity
    if quantity >= BULK_THRESHOLD:
        total *= 1 - BULK_DISCOUNT
    return round(total, 2)


def get_price(repo, sku: str) -> float:
    return repo.fetch(sku)
PY
cat > tests/test_price.py <<'PY'
import time
from unittest.mock import Mock

from app.price import get_price, line_total

CART = []


def test_get_price_returns_repo_value():
    repo = Mock()
    repo.fetch.return_value = 5
    assert get_price(repo, "sku-1") == 5


def test_discount_after_sleep():
    time.sleep(1)
    CART.append(line_total(2.0, 3))
    assert CART[-1] == 6.0


def test_cart_total_uses_previous_state():
    assert sum(CART) == 6.0


def test_bulk_discount_applies_at_ten_items():
    assert line_total(2.0, 9) == 18.0
    assert line_total(2.0, 10) == 18.0
PY
cat > pyproject.toml <<'TOML'
[project]
name = "price"
version = "0.1.0"

[tool.pytest.ini_options]
testpaths = ["tests"]
TOML
git init -q && git add -A && git -c user.email=eval@example.com -c user.name=eval commit -q -m init
