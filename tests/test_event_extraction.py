from adaptiveroute.data.demo_scenario import build_demo_scenario
from adaptiveroute.domain.events import EventType
from adaptiveroute.services.mutations import apply_event
from adaptiveroute.services.event_extraction import RuleBasedEventExtractor


def test_extracts_block_arc_event() -> None:
    scenario = build_demo_scenario()
    result = RuleBasedEventExtractor().extract("There was an accident between C7 and C6. Avoid that road.", scenario)

    assert result.event is not None
    assert result.event.type == EventType.BLOCK_ARC
    assert result.event.payload == {"from_node": "C7", "to_node": "C6", "bidirectional": True}


def test_extracts_portuguese_block_arc_event() -> None:
    scenario = build_demo_scenario()
    result = RuleBasedEventExtractor().extract("Há um bloqueio entre C1 e C3.", scenario)

    assert result.event is not None
    assert result.event.type == EventType.BLOCK_ARC
    assert result.event.payload == {"from_node": "C1", "to_node": "C3", "bidirectional": True}


def test_extracts_customer_unavailable_event() -> None:
    scenario = build_demo_scenario()
    result = RuleBasedEventExtractor().extract("Customer C3 cannot receive now.", scenario)

    assert result.event is not None
    assert result.event.type == EventType.CUSTOMER_UNAVAILABLE
    assert result.event.payload == {"customer_id": "C3"}


def test_extracts_unavailable_segment_as_block_arc_event() -> None:
    scenario = build_demo_scenario()
    result = RuleBasedEventExtractor().extract(
        "What if the segment between C3 and C5 becomes unavailable due to traffic?",
        scenario,
    )

    assert result.event is not None
    assert result.event.type == EventType.BLOCK_ARC
    assert result.event.payload == {"from_node": "C3", "to_node": "C5", "bidirectional": True}


def test_extracts_block_arc_for_known_inactive_customer_node() -> None:
    scenario = build_demo_scenario()
    unavailable = RuleBasedEventExtractor().extract("Customer C5 cannot receive now.", scenario)
    assert unavailable.event is not None
    mutated_scenario, _ = apply_event(scenario, unavailable.event)

    result = RuleBasedEventExtractor().extract(
        "For route ROUTE-001, what if the segment between C3 and C5 becomes unavailable due to traffic?",
        mutated_scenario,
    )

    assert result.event is not None
    assert result.event.type == EventType.BLOCK_ARC
    assert result.event.payload == {"from_node": "C3", "to_node": "C5", "bidirectional": True}


def test_extracts_priority_change_event() -> None:
    scenario = build_demo_scenario()
    result = RuleBasedEventExtractor().extract("C4 became urgent and should be high priority.", scenario)

    assert result.event is not None
    assert result.event.type == EventType.CUSTOMER_PRIORITY_CHANGE
    assert result.event.payload == {"customer_id": "C4", "priority": 3}


def test_rejects_unsupported_event() -> None:
    scenario = build_demo_scenario()
    result = RuleBasedEventExtractor().extract("Please make the route prettier.", scenario)

    assert result.event is None
    assert result.error
