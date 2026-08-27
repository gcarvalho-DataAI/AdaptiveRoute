from adaptiveroute.data.demo_scenario import build_demo_scenario
from adaptiveroute.domain.events import EventType, OperationalEvent
from adaptiveroute.services.mutations import apply_event


def test_block_arc_mutation_adds_bidirectional_block() -> None:
    scenario = build_demo_scenario()
    event = OperationalEvent(
        type=EventType.BLOCK_ARC,
        payload={"from_node": "C1", "to_node": "C2", "bidirectional": True},
        description="Accident between C1 and C2.",
    )

    mutated, mutation = apply_event(scenario, event)

    assert ("C1", "C2") in mutated.blocked_arcs
    assert ("C2", "C1") in mutated.blocked_arcs
    assert mutation.diff["bidirectional"] is True


def test_customer_unavailable_mutation_deactivates_customer() -> None:
    scenario = build_demo_scenario()
    event = OperationalEvent(
        type=EventType.CUSTOMER_UNAVAILABLE,
        payload={"customer_id": "C3"},
        description="Customer C3 cannot receive now.",
    )

    mutated, mutation = apply_event(scenario, event)

    customer = next(customer for customer in mutated.customers if customer.id == "C3")
    assert not customer.active
    assert not customer.required
    assert "C3" not in {customer.id for customer in mutated.active_customers}
    assert mutation.diff["customer_unavailable"] == "C3"
