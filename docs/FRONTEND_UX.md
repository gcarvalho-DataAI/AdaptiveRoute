# Frontend UX and Roles

The AdaptiveRoute frontend is a React/Vite operational console with role-aware workspaces. The PoC prioritizes clarity of the routing workflow over visual density: admins manage the operation; drivers interact only with their own routes.

## Roles

### Admin

Admin users can:

- inspect today's routes;
- select one or more routes on the dashboard map;
- create and manage scenarios;
- ingest orders from integration-style payloads or spreadsheets;
- start/cancel/delete planning jobs;
- manage drivers;
- inspect RAG/memory state;
- use the route chat for operational disruptions.

Admin login:

```text
admin@adaptiveroute.com
12345678
```

### Driver

Driver users can:

- see only routes assigned to their driver profile;
- inspect route map and route metrics;
- ask route-specific questions;
- report blocks, delays or unavailable customers;
- update route status;
- update password and vehicle capacity.

Driver credentials are created in the driver wizard.

## Admin Navigation

The admin sidebar contains:

- Dashboard;
- Route Chat;
- Scenarios;
- Drivers;
- Knowledge.

The old admin-side `Driver Portal` entry was removed because it mixed driver experience with admin operations. Driver workspace is now opened only after driver login.

## Driver Navigation

The driver sidebar contains:

- My Route;
- Profile.

`My Route` is the operational chat workspace. The driver does not need a separate home and chat flow because the primary action is route interaction.

## Dashboard Behavior

The admin dashboard is designed around route visibility:

- KPI cards summarize day/scenario state.
- The route selector supports search and pagination.
- Multiple route records can be selected.
- Selected routes are plotted on the map.
- If all routes are deselected, the map remains visible with scenario points but without route polylines.

This distinction is important:

- KPI planned distance represents total scenario/day distance.
- Route selection controls only visual route visibility on the map.

## Scenario Management UX

The scenario page supports:

- scenario listing with pagination and search;
- scenario creation wizard;
- ingestion from order integration payloads;
- spreadsheet upload;
- route optimization job start;
- job status/progress visibility;
- cancel/delete controls;
- scenario detail inspection.

The UI avoids labeling seeded/integration data as "mock" in user-facing copy. The PoC can use generated data internally, but the product language should remain operational.

## Driver Management UX

The driver page supports:

- driver roster;
- driver CRUD;
- driver creation wizard;
- vehicle capacity definition;
- login credential creation;
- driver deletion.

Route assignment is solver-owned. The driver wizard creates the user/vehicle/capacity record; it does not manually assign orders to the driver. After solver execution, generated route records are associated to drivers/vehicles.

When a driver is deleted, existing routes are retained for auditability and marked with a removed-driver reference rather than deleted.

## Chat UX

The route chat follows a GPT-like layout:

- conversation history on the left;
- active message thread in the center;
- agent execution trace, plan output and context window on the right.

The user writes naturally. The system extracts:

- route id;
- event type;
- affected nodes/customers;
- operational constraints.

The route selector should not be a hard requirement for chat. It can provide context, but the canonical binding comes from the user's message and stored route metadata.

## Driver Chat Scope

Driver chat is route-scoped:

- route id can be inferred from the driver's assigned route;
- messages can still mention route id explicitly;
- generated plans and maps are filtered to that driver's route only;
- the driver cannot inspect another driver's route.

## Trace and Debug Visibility

The UI exposes trace and context data because this is a technical PoC. The trace panel is useful for showing:

- event extraction;
- route lookup;
- route fact building;
- RAG usage;
- candidate generation source;
- validation;
- repair/fallback;
- response composition.

For a more production-oriented UI, trace panels can be hidden behind an admin-only debug mode.

## Current UX Limitations

- The frontend is implemented in a single large React file.
- Authentication is simplified.
- Some progress information is coarse because the solver does not expose reliable granular progress.
- Map routing depends on available OSRM data; otherwise fallback geometry is used.
- UI state is client-side and should be hardened for production.

## Recommended Frontend Refactor

Split `frontend/src/main.jsx` into:

```text
frontend/src/
  app/
    App.jsx
    navigation.js
  api/
    client.js
  components/
    Panel.jsx
    RouteMap.jsx
    FleetBoard.jsx
    PaginationControls.jsx
  views/
    DashboardView.jsx
    ChatView.jsx
    ScenariosView.jsx
    DriversView.jsx
    DriverChatView.jsx
    DriverProfileView.jsx
    KnowledgeView.jsx
  utils/
    routePlans.js
    formatting.js
```

This should be done after the PoC behavior stabilizes to avoid unnecessary churn during product validation.

