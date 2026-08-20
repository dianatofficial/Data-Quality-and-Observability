from src.ingestion.extractor import BatchExtractor
from src.ingestion.generator import EnterpriseDataGenerator


def test_generator_clean_orders():
    orders = EnterpriseDataGenerator.generate_clean_orders(count=20)
    assert len(orders) == 20
    for ord_dict in orders:
        assert ord_dict["order_id"].startswith("ORD-")
        assert ord_dict["total_amount"] > 0
        assert ord_dict["discount_amount"] <= ord_dict["total_amount"]
        assert ord_dict["currency"] in EnterpriseDataGenerator.CURRENCIES


def test_generator_corrupted_orders():
    orders = EnterpriseDataGenerator.generate_corrupted_orders(total_count=50, corruption_rate=0.40)
    assert len(orders) == 50


def test_generator_drifted_orders():
    orders = EnterpriseDataGenerator.generate_drifted_orders(count=10)
    assert len(orders) == 10
    for ord_dict in orders:
        assert "price_gross" in ord_dict
        assert "total_amount" not in ord_dict
        assert "loyalty_tier_v2" in ord_dict


def test_extractor_checksum():
    data = [{"id": 1, "name": "test"}, {"id": 2, "name": "sample"}]
    checksum1 = BatchExtractor.compute_batch_checksum(data)
    checksum2 = BatchExtractor.compute_batch_checksum(data)
    assert checksum1 == checksum2
    assert len(checksum1) == 64
