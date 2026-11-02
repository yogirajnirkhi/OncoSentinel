"""
Tests for Federated Learning Simulation & Out-of-Site Generalization (FR-23, Pati et al. 2022)
"""
from __future__ import annotations

from services.federated.coordinator import FederatedCoordinator


def test_federated_round_execution():
    coordinator = FederatedCoordinator()
    round_result = coordinator.execute_round(target_category="breast", num_participating_sites=3)

    assert round_result.round_id == 1
    assert len(round_result.participating_sites) == 3
    assert round_result.total_local_samples > 300
    assert round_result.unseen_site_auc >= 0.88
    assert round_result.out_of_site_improvement_pct >= 10.0
    assert round_result.aggregation_status == "SUCCESS"
