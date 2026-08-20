import os
from pathlib import Path
from typing import Any, Dict, Generator, List

import pytest
from sqlalchemy.orm import Session

from config.settings import AppSettings, get_settings
from src.core.engine import GatekeeperEngine
from src.storage.database import DatabaseManager


@pytest.fixture(scope="session")
def test_settings() -> AppSettings:
    settings = get_settings()
    settings.environment = "test"
    settings.database_url = "sqlite:///:memory:"
    return settings


@pytest.fixture
def db_session(test_settings: AppSettings) -> Generator[Session, None, None]:
    db_mgr = DatabaseManager(database_url="sqlite:///:memory:")
    db_mgr.init_schema()
    with db_mgr.get_session() as session:
        yield session


@pytest.fixture
def gatekeeper_engine() -> GatekeeperEngine:
    return GatekeeperEngine()


@pytest.fixture
def sample_clean_orders() -> List[Dict[str, Any]]:
    return [
        {
            "order_id": "ORD-11223344AA",
            "customer_id": "CUST-1001",
            "total_amount": 199.99,
            "discount_amount": 10.00,
            "currency": "USD",
            "status": "COMPLETED",
            "order_timestamp": "2026-08-20T10:00:00",
            "items_count": 2,
            "shipping_country": "US",
        },
        {
            "order_id": "ORD-55667788BB",
            "customer_id": "CUST-1002",
            "total_amount": 49.50,
            "discount_amount": 0.00,
            "currency": "EUR",
            "status": "PENDING",
            "order_timestamp": "2026-08-20T10:15:00",
            "items_count": 1,
            "shipping_country": "DE",
        },
    ]


@pytest.fixture
def sample_corrupted_orders() -> List[Dict[str, Any]]:
    return [
        {
            # Clean record
            "order_id": "ORD-VALID001",
            "customer_id": "CUST-1001",
            "total_amount": 100.0,
            "discount_amount": 10.0,
            "currency": "USD",
            "status": "COMPLETED",
            "order_timestamp": "2026-08-20T10:00:00",
        },
        {
            # Anomaly: Null order_id, negative amount, invalid currency
            "order_id": None,
            "customer_id": "CUST-1002",
            "total_amount": -50.0,
            "discount_amount": 0.0,
            "currency": "INVALID_TOKEN",
            "status": "PENDING",
            "order_timestamp": "2026-08-20T10:00:00",
        },
        {
            # Anomaly: discount > total_amount
            "order_id": "ORD-DISCFAIL",
            "customer_id": "CUST-1003",
            "total_amount": 30.0,
            "discount_amount": 100.0,
            "currency": "USD",
            "status": "PENDING",
            "order_timestamp": "2026-08-20T10:00:00",
        },
    ]
