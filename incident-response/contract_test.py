"""A trusted calendar contract used to check the agent's proposed source change."""
from datetime import datetime, timedelta, timezone

import pytest
from app.main import order_detail


@pytest.mark.parametrize("date", ["2026-01-31", "2026-02-28", "2024-02-29", "2026-04-30", "2026-12-31", "2026-09-15"])
def test_express_delivery_crosses_month_and_year_boundaries(date):
    placed = datetime.fromisoformat(date).replace(tzinfo=timezone.utc)
    order = {"id": "synthetic", "priority": "express", "created_at": placed.isoformat()}
    assert order_detail(order)["estimated_delivery"] == (placed + timedelta(days=2)).date().isoformat()


def test_standard_orders_do_not_gain_a_delivery_date():
    order = {"id": "synthetic", "priority": "standard", "created_at": "2026-01-31T00:00:00+00:00"}
    assert order_detail(order) == order
