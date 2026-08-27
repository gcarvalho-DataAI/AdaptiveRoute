# AdaptiveRoute Route Question Answering Grounding Guide

This document supports retrieval-augmented answers for questions about an operational route.

## Source priority

When answering route questions, route facts from the operational database are authoritative. Retrieved documentation explains semantics and policy, but it must not override the current route record.

Priority order:

1. Current route facts: route id, scenario id, driver id, driver status, vehicle id, route status, stop sequence, total distance, load, capacity and validation data.
2. Retrieved documentation: operational definitions, safety rules, and interpretation guidance.
3. Conversation memory: previous user messages and assistant answers, only for continuity.

If a value is not present in route facts, the assistant should say that the value is not available instead of inventing it.

## Stop sequence semantics

Route stop sequences usually start and end at the depot. The depot is not a delivery stop.

For a sequence such as:

```text
D0 -> C8 -> C7 -> C6 -> C5 -> C4 -> D0
```

- `D0` at the beginning is the departure depot.
- `C8` is the first delivery stop.
- Intermediate `C*` nodes are customer delivery stops.
- `D0` at the end is the return depot.

When the user asks for the first delivery, first customer, first stop after leaving the depot, or next operational delivery, the answer should use the first customer node after the depot, not the depot itself.

## Capacity and feasibility semantics

Capacity feasibility should be evaluated from load and capacity facts:

```text
capacity_slack = vehicle_capacity - total_load
```

- If `capacity_slack >= 0`, the route is feasible from a capacity standpoint.
- If `capacity_slack < 0`, the route violates capacity.
- If capacity is missing, capacity feasibility is unknown.

The answer should include the numeric load, capacity, and slack whenever available.

## Driver assignment semantics

The route driver id identifies the driver currently associated with the operational route.

If a driver was removed, route metadata may preserve the historical driver snapshot and the route driver id may be prefixed with `removed:`. In that case, the assistant should explain that the route is historical or currently unassigned and should not imply that the removed driver can still operate it.

## Replanning versus route Q&A

Route Q&A answers questions about the current stored route. It should not produce a new route plan unless the user explicitly reports an operational event requiring replanning, such as a blocked road, accident, unavailable customer, delay, capacity problem, or priority change.

If the user asks whether a route is feasible, what the stops are, who the driver is, what the first delivery is, or what should be checked before departure, answer from current route facts.

If the user reports a blocked arc or delivery disruption, the agent should enter the replanning workflow instead of only answering a static route question.

## What-if replanning response policy

When the user asks a what-if question that contains an operational event, treat it as a scenario assessment:

- "what if customer C5 cannot receive" is a customer-unavailable event;
- "what if the segment between C3 and C5 is unavailable" is a blocked-arc event;
- "what if C2 becomes urgent" is a priority-change event.

The explanatory response should be generated after the plan is solved and validated. It must explain:

1. the interpreted event;
2. whether the candidate passed validation;
3. what changed in the stop sequence or served customer set;
4. distance impact versus the previous/base plan;
5. whether any customer was removed, deferred, or no longer served by the candidate;
6. the recommended operational next action.

If `removed_customers` is not empty, do not frame a lower distance as a pure improvement. A shorter distance can happen because a stop was removed or deferred. State that explicitly.

If `distance_delta` is zero, explain that the candidate preserves total route distance under the modeled distance matrix, even if the stop ordering or blocked-arc constraints changed.

The assistant must not claim real-time ETA, live traffic, customer confirmation, or driver GPS state unless those facts are present in the route facts or retrieved context.

## Operational answer style

Answers should be concise and operational. Prefer direct statements:

- route identifier;
- driver and vehicle;
- current status;
- first delivery stop;
- full stop sequence when relevant;
- distance;
- load, capacity, and slack;
- warning if facts are missing or driver was removed.

Do not present deterministic documentation as real-time telemetry. Do not claim live traffic, ETA, GPS position, weather, or customer confirmation unless those facts are explicitly present in the route facts or retrieved context.
