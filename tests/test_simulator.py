from src.core.models import ValidationStatus
from src.dashboard.simulator import LiveSimulationEngine


def test_simulation_engine_initialization():
    sim = LiveSimulationEngine()
    assert len(sim.batch_history) > 0
    assert sim.latest_summary is not None
    assert len(sim.clean_orders) > 0


def test_simulation_engine_run_batch():
    sim = LiveSimulationEngine()
    initial_history_len = len(sim.batch_history)
    
    summary = sim.run_simulation_batch(batch_type="clean", total_records=30)
    assert summary.passed_records == 30
    assert summary.quarantined_records == 0
    assert len(sim.batch_history) == initial_history_len + 1


def test_simulation_engine_resolve_quarantine():
    sim = LiveSimulationEngine()
    
    # Run a corrupted batch to ensure we have quarantine records
    sim.run_simulation_batch(batch_type="mixed", total_records=50)
    quarantined = sim.get_quarantine_records(status="QUARANTINED")
    assert len(quarantined) > 0
    
    target_id = quarantined[0]["quarantine_id"]
    resolved = sim.resolve_quarantine_record(
        quarantine_id=target_id,
        action="RECONCILE",
        notes="Approved by engineer in test",
    )
    assert resolved is True
    
    reconciled_records = sim.get_quarantine_records(status="RECONCILED")
    assert any(r["quarantine_id"] == target_id for r in reconciled_records)
    assert len(sim.audit_log) > 0
