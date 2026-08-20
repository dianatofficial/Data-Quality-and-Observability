import random
from datetime import datetime, timedelta
from typing import Any, Dict, List
from uuid import uuid4


class EnterpriseDataGenerator:
    """Generates realistic e-commerce orders, customer profiles, and anomaly-injected batches."""

    CURRENCIES = ["USD", "EUR", "GBP", "CAD", "AUD", "JPY"]
    STATUSES = ["PENDING", "PROCESSING", "COMPLETED", "CANCELLED", "REFUNDED"]
    COUNTRIES = ["US", "DE", "GB", "CA", "AU", "FR", "JP"]

    @classmethod
    def generate_clean_orders(cls, count: int = 100) -> List[Dict[str, Any]]:
        records: List[Dict[str, Any]] = []
        base_time = datetime.utcnow() - timedelta(days=2)

        for i in range(count):
            order_id = f"ORD-{uuid4().hex[:10].upper()}"
            customer_id = f"CUST-{random.randint(1000, 9999)}"
            total = round(random.uniform(15.0, 1250.0), 2)
            discount = round(random.uniform(0.0, total * 0.3), 2)
            ts = (base_time + timedelta(seconds=i * 30)).strftime("%Y-%m-%dT%H:%M:%S")

            records.append({
                "order_id": order_id,
                "customer_id": customer_id,
                "total_amount": total,
                "discount_amount": discount,
                "currency": random.choice(cls.CURRENCIES),
                "status": random.choice(cls.STATUSES),
                "order_timestamp": ts,
                "items_count": random.randint(1, 8),
                "shipping_country": random.choice(cls.COUNTRIES),
            })
        return records

    @classmethod
    def generate_corrupted_orders(
        cls, total_count: int = 100, corruption_rate: float = 0.20
    ) -> List[Dict[str, Any]]:
        """Generates a batch where a portion of records violate data quality rules."""
        records = cls.generate_clean_orders(total_count)
        corrupted_count = int(total_count * corruption_rate)
        indices_to_corrupt = random.sample(range(total_count), min(corrupted_count, total_count))

        anomaly_types = [
            "null_order_id",
            "negative_amount",
            "invalid_currency",
            "future_timestamp",
            "discount_exceeds_total",
            "invalid_status",
            "null_customer_id",
            "type_mismatch_string_amount",
        ]

        for idx in indices_to_corrupt:
            anomaly = random.choice(anomaly_types)
            rec = records[idx]

            if anomaly == "null_order_id":
                rec["order_id"] = None
            elif anomaly == "negative_amount":
                rec["total_amount"] = -round(random.uniform(10.0, 200.0), 2)
            elif anomaly == "invalid_currency":
                rec["currency"] = "XYZ_TOKEN"
            elif anomaly == "future_timestamp":
                rec["order_timestamp"] = (datetime.utcnow() + timedelta(days=10)).strftime("%Y-%m-%dT%H:%M:%S")
            elif anomaly == "discount_exceeds_total":
                rec["total_amount"] = 50.0
                rec["discount_amount"] = 150.0
            elif anomaly == "invalid_status":
                rec["status"] = "UNKNOWN_GLITCH_STATE"
            elif anomaly == "null_customer_id":
                rec["customer_id"] = ""
            elif anomaly == "type_mismatch_string_amount":
                rec["total_amount"] = "INVALID_NOT_A_FLOAT"

        return records

    @classmethod
    def generate_drifted_orders(cls, count: int = 100) -> List[Dict[str, Any]]:
        """Generates a batch with structural schema drift (renamed column & unexpected columns)."""
        records = cls.generate_clean_orders(count)
        for rec in records:
            # Drop total_amount and replace with price_gross (schema mutation)
            amount = rec.pop("total_amount")
            rec["price_gross"] = amount
            rec["loyalty_tier_v2"] = "PLATINUM"
            rec["experimental_ml_score"] = 0.942
        return records

    @classmethod
    def generate_customers(cls, count: int = 100, corrupted_count: int = 10) -> List[Dict[str, Any]]:
        records: List[Dict[str, Any]] = []
        domains = ["gmail.com", "company.org", "outlook.com", "enterprise.io"]

        for i in range(count):
            cid = f"CUST-{1000 + i}"
            email = f"user_{i}@{random.choice(domains)}"
            signup = (datetime.utcnow() - timedelta(days=random.randint(1, 365))).strftime("%Y-%m-%d")
            country = random.choice(cls.COUNTRIES)
            age = random.randint(18, 75)

            records.append({
                "customer_id": cid,
                "email": email,
                "signup_date": signup,
                "country_code": country,
                "age": age,
                "is_active": True,
            })

        # Inject anomalies into last `corrupted_count`
        for i in range(min(corrupted_count, count)):
            idx = count - 1 - i
            choice = i % 3
            if choice == 0:
                records[idx]["email"] = "not_an_email_at_all"
            elif choice == 1:
                records[idx]["customer_id"] = None
            elif choice == 2:
                records[idx]["age"] = -5

        return records
