from __future__ import annotations

from dataclasses import dataclass
from time import perf_counter

import pyomo.environ as pyo

from adaptiveroute.domain.models import RoutingPlan, RoutingScenario, SolveStatus, SolverResult, VehicleRoute
from adaptiveroute.solvers.base import RoutingEngine


@dataclass(frozen=True)
class PyomoHighsEngine(RoutingEngine):
    time_limit_seconds: float | None = None
    mip_gap: float | None = None

    def solve(self, scenario: RoutingScenario) -> SolverResult:
        started_at = perf_counter()
        try:
            model = self._build_model(scenario)
            solver = pyo.SolverFactory("appsi_highs")
            if not solver.available(False):
                return SolverResult(
                    status=SolveStatus.ERROR,
                    plan=None,
                    message="HiGHS solver is not available. Run `uv sync` to install highspy.",
                )

            if self.time_limit_seconds is not None:
                solver.config.time_limit = self.time_limit_seconds
                solver.highs_options["time_limit"] = self.time_limit_seconds
            if self.mip_gap is not None:
                solver.config.mip_gap = self.mip_gap
                solver.highs_options["mip_rel_gap"] = self.mip_gap
            result = solver.solve(model)
            solve_time_ms = (perf_counter() - started_at) * 1000
            termination = result.solver.termination_condition

            if termination == pyo.TerminationCondition.optimal:
                plan = self._extract_plan(scenario, model)
                return SolverResult(status=SolveStatus.OPTIMAL, plan=plan, solve_time_ms=solve_time_ms)

            if termination in {
                pyo.TerminationCondition.feasible,
                pyo.TerminationCondition.maxTimeLimit,
                pyo.TerminationCondition.maxIterations,
            }:
                plan = self._extract_plan(scenario, model)
                return SolverResult(
                    status=SolveStatus.FEASIBLE,
                    plan=plan,
                    message=f"Solver terminated with {termination}.",
                    solve_time_ms=solve_time_ms,
                )

            if termination == pyo.TerminationCondition.infeasible:
                return SolverResult(
                    status=SolveStatus.INFEASIBLE,
                    plan=None,
                    message="Scenario is infeasible.",
                    solve_time_ms=solve_time_ms,
                )

            return SolverResult(
                status=SolveStatus.ERROR,
                plan=None,
                message=f"Solver terminated with {termination}.",
                solve_time_ms=solve_time_ms,
            )
        except Exception as exc:  # pragma: no cover - defensive boundary for CLI/API usage.
            return SolverResult(
                status=SolveStatus.ERROR,
                plan=None,
                message=str(exc),
                solve_time_ms=(perf_counter() - started_at) * 1000,
            )

    def _build_model(self, scenario: RoutingScenario) -> pyo.ConcreteModel:
        customers = [customer.id for customer in scenario.active_customers]
        vehicles = [vehicle.id for vehicle in scenario.vehicles]
        nodes = [scenario.depot.id, *customers]
        arcs = [(i, j) for i in nodes for j in nodes if i != j]
        customer_by_id = {customer.id: customer for customer in scenario.active_customers}
        vehicle_by_id = {vehicle.id: vehicle for vehicle in scenario.vehicles}
        n_customers = len(customers)

        model = pyo.ConcreteModel()
        model.N = pyo.Set(initialize=nodes)
        model.C = pyo.Set(initialize=customers)
        model.K = pyo.Set(initialize=vehicles)
        model.A = pyo.Set(initialize=arcs, dimen=2)

        model.x = pyo.Var(model.A, model.K, within=pyo.Binary)
        model.y = pyo.Var(model.C, model.K, within=pyo.Binary)
        model.used = pyo.Var(model.K, within=pyo.Binary)
        model.u = pyo.Var(model.C, model.K, bounds=(0, n_customers), within=pyo.NonNegativeReals)

        def objective_rule(m: pyo.ConcreteModel) -> pyo.Expression:
            return sum(scenario.distance(i, j) * m.x[i, j, k] for (i, j) in m.A for k in m.K)

        model.objective = pyo.Objective(rule=objective_rule, sense=pyo.minimize)

        def visit_once_rule(m: pyo.ConcreteModel, customer: str) -> pyo.Expression:
            return sum(m.y[customer, vehicle] for vehicle in m.K) == 1

        model.visit_once = pyo.Constraint(model.C, rule=visit_once_rule)

        def flow_out_rule(m: pyo.ConcreteModel, customer: str, vehicle: str) -> pyo.Expression:
            return sum(m.x[customer, j, vehicle] for j in m.N if j != customer) == m.y[customer, vehicle]

        model.flow_out = pyo.Constraint(model.C, model.K, rule=flow_out_rule)

        def flow_in_rule(m: pyo.ConcreteModel, customer: str, vehicle: str) -> pyo.Expression:
            return sum(m.x[i, customer, vehicle] for i in m.N if i != customer) == m.y[customer, vehicle]

        model.flow_in = pyo.Constraint(model.C, model.K, rule=flow_in_rule)

        depot_id = scenario.depot.id

        def depot_out_rule(m: pyo.ConcreteModel, vehicle: str) -> pyo.Expression:
            return sum(m.x[depot_id, j, vehicle] for j in m.N if j != depot_id) == m.used[vehicle]

        model.depot_out = pyo.Constraint(model.K, rule=depot_out_rule)

        def depot_in_rule(m: pyo.ConcreteModel, vehicle: str) -> pyo.Expression:
            return sum(m.x[i, depot_id, vehicle] for i in m.N if i != depot_id) == m.used[vehicle]

        model.depot_in = pyo.Constraint(model.K, rule=depot_in_rule)

        def used_if_customer_assigned_rule(m: pyo.ConcreteModel, customer: str, vehicle: str) -> pyo.Expression:
            return m.y[customer, vehicle] <= m.used[vehicle]

        model.used_if_customer_assigned = pyo.Constraint(model.C, model.K, rule=used_if_customer_assigned_rule)

        def capacity_rule(m: pyo.ConcreteModel, vehicle: str) -> pyo.Expression:
            return (
                sum(customer_by_id[customer].demand * m.y[customer, vehicle] for customer in m.C)
                <= vehicle_by_id[vehicle].capacity
            )

        model.capacity = pyo.Constraint(model.K, rule=capacity_rule)

        def blocked_arc_rule(m: pyo.ConcreteModel, i: str, j: str, vehicle: str) -> pyo.Expression:
            if (i, j) not in scenario.blocked_arcs:
                return pyo.Constraint.Skip
            return m.x[i, j, vehicle] == 0

        model.blocked_arcs = pyo.Constraint(model.A, model.K, rule=blocked_arc_rule)

        def mtz_rule(m: pyo.ConcreteModel, i: str, j: str, vehicle: str) -> pyo.Expression:
            if i == j:
                return pyo.Constraint.Skip
            return m.u[i, vehicle] - m.u[j, vehicle] + n_customers * m.x[i, j, vehicle] <= n_customers - 1

        model.mtz = pyo.Constraint(model.C, model.C, model.K, rule=mtz_rule)

        def order_upper_rule(m: pyo.ConcreteModel, customer: str, vehicle: str) -> pyo.Expression:
            return m.u[customer, vehicle] <= n_customers * m.y[customer, vehicle]

        model.order_upper = pyo.Constraint(model.C, model.K, rule=order_upper_rule)

        def order_lower_rule(m: pyo.ConcreteModel, customer: str, vehicle: str) -> pyo.Expression:
            return m.u[customer, vehicle] >= m.y[customer, vehicle]

        model.order_lower = pyo.Constraint(model.C, model.K, rule=order_lower_rule)

        return model

    def _extract_plan(self, scenario: RoutingScenario, model: pyo.ConcreteModel) -> RoutingPlan:
        customer_by_id = {customer.id: customer for customer in scenario.active_customers}
        routes: list[VehicleRoute] = []

        for vehicle in scenario.vehicles:
            route = [scenario.depot.id]
            current = scenario.depot.id
            visited: set[str] = set()

            while True:
                next_nodes = [
                    j
                    for j in model.N
                    if j != current and (current, j) in model.A and pyo.value(model.x[current, j, vehicle.id]) > 0.5
                ]
                if not next_nodes:
                    break
                next_node = sorted(next_nodes)[0]
                route.append(next_node)
                if next_node == scenario.depot.id:
                    break
                if next_node in visited:
                    break
                visited.add(next_node)
                current = next_node

            if len(route) == 1:
                continue

            distance = sum(scenario.distance(route[idx], route[idx + 1]) for idx in range(len(route) - 1))
            load = sum(customer_by_id[node_id].demand for node_id in route if node_id in customer_by_id)
            routes.append(
                VehicleRoute(
                    vehicle_id=vehicle.id,
                    stops=tuple(route),
                    load=load,
                    distance=round(distance, 2),
                )
            )

        total_distance = round(sum(route.distance for route in routes), 2)
        return RoutingPlan(scenario_id=scenario.id, routes=tuple(routes), total_distance=total_distance)
