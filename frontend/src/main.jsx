import React, { useEffect, useMemo, useRef, useState } from "react";
import { createRoot } from "react-dom/client";
import { CircleMarker, MapContainer, Polyline, Popup, TileLayer, Tooltip, useMap } from "react-leaflet";
import {
  Bot,
  BrainCircuit,
  Bug,
  ChevronLeft,
  ChevronRight,
  Database,
  Gauge,
  Layers3,
  LogIn,
  LogOut,
  MapPinned,
  MessageSquareText,
  Navigation,
  Play,
  Radar,
  RefreshCw,
  Route,
  Search,
  Send,
  Settings2,
  ShieldCheck,
  Square,
  Trash2,
  Truck,
  Users,
  UploadCloud,
  Zap,
} from "lucide-react";
import "leaflet/dist/leaflet.css";
import "./styles.css";

const API_DEFAULT = import.meta.env.VITE_ADAPTIVEROUTE_API_BASE_URL || "http://127.0.0.1:8090";

const NAV_ITEMS = [
  { id: "dashboard", label: "Dashboard", icon: Gauge },
  { id: "chat", label: "Route Chat", icon: Bot },
  { id: "scenarios", label: "Scenarios", icon: Layers3 },
  { id: "drivers", label: "Drivers", icon: Users },
  { id: "knowledge", label: "Knowledge", icon: Database },
];

const DRIVER_NAV_ITEMS = [
  { id: "driverWorkspace", label: "My Route", icon: MapPinned },
  { id: "driverProfile", label: "Profile", icon: Settings2 },
];

const DEMO_LOCATIONS = {
  D0: {
    label: "Manhattan Micro-Fulfillment Hub",
    address: "Pier 57, 25 11th Ave, New York, NY",
    lat: 40.7431,
    lng: -74.0106,
    type: "depot",
  },
  C1: {
    label: "Chelsea Market",
    address: "75 9th Ave, New York, NY",
    lat: 40.7424,
    lng: -74.006,
    type: "customer",
  },
  C2: {
    label: "Flatiron District Office",
    address: "175 5th Ave, New York, NY",
    lat: 40.7411,
    lng: -73.9897,
    type: "customer",
  },
  C3: {
    label: "Union Square Pickup",
    address: "14th St & Union Square W, New York, NY",
    lat: 40.7359,
    lng: -73.9911,
    type: "customer",
  },
  C4: {
    label: "SoHo Retail Dock",
    address: "Prince St & Broadway, New York, NY",
    lat: 40.7248,
    lng: -73.9973,
    type: "customer",
  },
  C5: {
    label: "Lower East Side Pharmacy",
    address: "Delancey St & Essex St, New York, NY",
    lat: 40.7188,
    lng: -73.9888,
    type: "customer",
  },
  C6: {
    label: "Brooklyn Navy Yard Gate",
    address: "141 Flushing Ave, Brooklyn, NY",
    lat: 40.6987,
    lng: -73.9724,
    type: "customer",
  },
  C7: {
    label: "DUMBO Warehouse",
    address: "55 Water St, Brooklyn, NY",
    lat: 40.7033,
    lng: -73.9903,
    type: "customer",
  },
  C8: {
    label: "Battery Park Dropoff",
    address: "Battery Pl, New York, NY",
    lat: 40.7033,
    lng: -74.017,
    type: "customer",
  },
};

const ROUTE_COLORS = ["#27d6ff", "#8b5cf6", "#2df59d", "#ffb020"];
const PAGE_SIZE = 6;
const AUTH_STORAGE_KEY = "adaptiveroute.session";

const DAILY_ORDER_LOCATIONS = [
  ["Chelsea Market", "75 9th Ave, New York, NY", 40.7424, -74.006],
  ["Flatiron District Office", "175 5th Ave, New York, NY", 40.7411, -73.9897],
  ["Union Square Retail", "14th St & Union Square W, New York, NY", 40.7359, -73.9911],
  ["SoHo Retail Dock", "Prince St & Broadway, New York, NY", 40.7248, -73.9973],
  ["Lower East Side Pharmacy", "Delancey St & Essex St, New York, NY", 40.7188, -73.9888],
  ["Brooklyn Navy Yard Gate", "141 Flushing Ave, Brooklyn, NY", 40.6987, -73.9724],
  ["DUMBO Warehouse", "55 Water St, Brooklyn, NY", 40.7033, -73.9903],
  ["Battery Park Dropoff", "Battery Pl, New York, NY", 40.7033, -74.017],
  ["Tribeca Clinic", "310 Greenwich St, New York, NY", 40.7174, -74.0101],
  ["World Trade Center Office", "285 Fulton St, New York, NY", 40.7127, -74.0134],
  ["Chinatown Market", "Canal St & Mott St, New York, NY", 40.7165, -73.9972],
  ["East Village Grocery", "1st Ave & E 9th St, New York, NY", 40.7291, -73.9866],
  ["Gramercy Medical", "E 23rd St & 2nd Ave, New York, NY", 40.7382, -73.9816],
  ["Hudson Yards Tower", "34th St & 11th Ave, New York, NY", 40.7538, -74.0022],
  ["Times Square Retail", "W 42nd St & 7th Ave, New York, NY", 40.7561, -73.9869],
  ["Grand Central Office", "89 E 42nd St, New York, NY", 40.7527, -73.9772],
  ["Upper West Side Clinic", "W 72nd St & Broadway, New York, NY", 40.7789, -73.9813],
  ["Upper East Side Pharmacy", "E 86th St & Lexington Ave, New York, NY", 40.7794, -73.9557],
  ["Harlem Community Hub", "125th St & Lenox Ave, New York, NY", 40.8075, -73.9459],
  ["Columbia Area Dropoff", "Broadway & W 116th St, New York, NY", 40.8079, -73.963],
  ["Williamsburg Retail", "Bedford Ave & N 7th St, Brooklyn, NY", 40.7179, -73.9575],
  ["Greenpoint Pharmacy", "Manhattan Ave & Greenpoint Ave, Brooklyn, NY", 40.7309, -73.954],
  ["Downtown Brooklyn Office", "Jay St & Willoughby St, Brooklyn, NY", 40.6926, -73.9875],
  ["Park Slope Market", "5th Ave & Union St, Brooklyn, NY", 40.6774, -73.9831],
  ["Gowanus Fulfillment", "3rd Ave & 9th St, Brooklyn, NY", 40.6736, -73.9942],
  ["Long Island City Dock", "44th Dr & Vernon Blvd, Queens, NY", 40.7474, -73.9548],
  ["Astoria Pharmacy", "31st St & Ditmars Blvd, Queens, NY", 40.7766, -73.9126],
  ["Sunnyside Grocery", "Queens Blvd & 46th St, Queens, NY", 40.7433, -73.9185],
  ["Jackson Heights Clinic", "37th Ave & 82nd St, Queens, NY", 40.7506, -73.8838],
  ["Maspeth Warehouse", "Grand Ave & 69th St, Queens, NY", 40.7246, -73.8964],
  ["Hoboken Waterfront", "1 Hudson Pl, Hoboken, NJ", 40.7359, -74.0292],
  ["Jersey City Exchange Place", "Exchange Pl, Jersey City, NJ", 40.7161, -74.0338],
  ["Newport Retail", "30 Mall Dr W, Jersey City, NJ", 40.7272, -74.0384],
  ["Fort Greene Clinic", "DeKalb Ave & S Portland Ave, Brooklyn, NY", 40.6897, -73.9749],
  ["Red Hook Dock", "Van Brunt St & Beard St, Brooklyn, NY", 40.6727, -74.0112],
  ["Carroll Gardens Dropoff", "Court St & Carroll St, Brooklyn, NY", 40.6807, -73.9966],
];

const DAILY_LOCATION_LOOKUP = DAILY_ORDER_LOCATIONS.reduce(
  (locations, [label, address, lat, lng], index) => ({
    ...locations,
    [`C${index + 1}`]: { label, address, lat, lng, type: "customer" },
  }),
  {},
);

const DAILY_ORDER_WEIGHTS = [2, 3, 2, 4, 1, 3, 2, 2, 4, 3, 1, 2, 3];
const DAILY_ORDER_VOLUMES = [0.8, 1.0, 0.7, 1.4, 0.5, 1.1, 0.8, 0.9, 1.3, 1.0, 0.6, 0.7, 1.0];
const DAILY_ORDER_PRIORITIES = [2, 1, 1, 3, 1, 2, 1, 2, 2, 1, 3, 1, 2];
const DAILY_MANIFEST_MIN_ORDERS = 10;
const DAILY_MANIFEST_MAX_ORDERS = 13;

function buildDailyOrdersScenario(name = "NYC Morning Dispatch") {
  const runId = new Date().toISOString().replace(/\D/g, "").slice(0, 14);
  const randomSuffix = Math.random().toString(36).slice(2, 6);
  const orderCount = randomInt(DAILY_MANIFEST_MIN_ORDERS, DAILY_MANIFEST_MAX_ORDERS);
  const scenarioSlug = slugifyScenarioName(name) || "nyc-route-plan";
  return {
    id: `${scenarioSlug}-${orderCount}-${runId}-${randomSuffix}`,
    depot: {
      address: DEMO_LOCATIONS.D0.address,
      lat: DEMO_LOCATIONS.D0.lat,
      lng: DEMO_LOCATIONS.D0.lng,
    },
    orders: DAILY_ORDER_LOCATIONS.slice(0, orderCount).map(([label, address, lat, lng], index) => {
      const demandVariation = randomInt(-1, 1);
      const weight = Math.max(1, DAILY_ORDER_WEIGHTS[index] + demandVariation);
      const volume = Math.max(0.4, Number((DAILY_ORDER_VOLUMES[index] + randomInt(-1, 1) * 0.1).toFixed(1)));
      const priority = clamp(DAILY_ORDER_PRIORITIES[index] + randomInt(-1, 1), 1, 3);
      return {
        id: `ORDER-${runId}-${String(index + 1).padStart(3, "0")}`,
        pickup: {
          address: DEMO_LOCATIONS.D0.address,
          lat: DEMO_LOCATIONS.D0.lat,
          lng: DEMO_LOCATIONS.D0.lng,
        },
        delivery: {
          address,
          lat,
          lng,
        },
        weight,
        weight_unit: "kg",
        volume,
        volume_unit: "m3",
        priority,
        description: `Operational manifest delivery · ${label}`,
      };
    }),
    vehicle_count: 6,
    vehicle_capacity: 24,
  };
}

function App() {
  const [activeView, setActiveView] = useState("dashboard");
  const [apiBaseUrl, setApiBaseUrl] = useState(API_DEFAULT);
  const [status, setStatus] = useState({ text: "Idle", level: "idle" });
  const [authSession, setAuthSession] = useState(() => readStoredSession());
  const [now, setNow] = useState(() => Date.now());
  const [routes, setRoutes] = useState([]);
  const [scenarios, setScenarios] = useState([]);
  const [planningJobs, setPlanningJobs] = useState([]);
  const [driverRecords, setDriverRecords] = useState([]);
  const [selectedRoute, setSelectedRoute] = useState(null);
  const [selectedRouteIds, setSelectedRouteIds] = useState(null);
  const [dashboardScenarioId, setDashboardScenarioId] = useState(null);
  const [selectedScenario, setSelectedScenario] = useState(null);
  const [conversations, setConversations] = useState([]);
  const [conversationId, setConversationId] = useState(null);
  const [agenticResult, setAgenticResult] = useState(null);
  const [contextWindow, setContextWindow] = useState(null);
  const [messages, setMessages] = useState([]);
  const [ragOutput, setRagOutput] = useState(null);
  const [mapGeometry, setMapGeometry] = useState(null);
  const [driverSession, setDriverSession] = useState(null);
  const [driverProfileForm, setDriverProfileForm] = useState({ capacity: "", newPassword: "" });
  const [form, setForm] = useState({
    routeId: "ROUTE-001",
    driverId: "DRV-MANHATTAN-01",
    driverName: "Maya Chen",
    vehicleId: "VAN-MH-014",
    capacity: "22",
    region: "Manhattan South",
    driverStatus: "available",
    shiftStart: "08:00",
    shiftEnd: "16:00",
    username: "maya.chen",
    password: "route-demo-01",
    loginUsername: "maya.chen",
    loginPassword: "route-demo-01",
    scenarioId: "demo-cvrp-8",
    status: "in_progress",
  });
  const [message, setMessage] = useState("");

  const api = useMemo(() => apiBaseUrl.replace(/\/$/, ""), [apiBaseUrl]);
  const currentPlan = selectedRoute?.current_plan ?? extractGeneratedPlan(agenticResult) ?? null;
  const dashboardScenarioOptions = useMemo(() => buildDashboardScenarioOptions(routes, scenarios), [routes, scenarios]);
  const activeDashboardScenarioId = useMemo(
    () => resolveDashboardScenarioId(dashboardScenarioId, dashboardScenarioOptions),
    [dashboardScenarioId, dashboardScenarioOptions],
  );
  const dashboardRoutes = useMemo(
    () => (activeDashboardScenarioId ? routes.filter((route) => route.scenario_id === activeDashboardScenarioId) : []),
    [routes, activeDashboardScenarioId],
  );
  const selectedDashboardRouteIds = useMemo(
    () => (selectedRouteIds === null ? dashboardRoutes.map((route) => route.id) : selectedRouteIds),
    [selectedRouteIds, dashboardRoutes],
  );
  const selectedDashboardRoutes = useMemo(
    () => dashboardRoutes.filter((route) => selectedDashboardRouteIds.includes(route.id)),
    [dashboardRoutes, selectedDashboardRouteIds],
  );
  const scenarioLocations = useMemo(() => buildScenarioLocations(selectedScenario), [selectedScenario]);
  const drivers = useMemo(() => mergeDriversWithRoutes(driverRecords, routes), [driverRecords, routes]);
  const dashboardRouteTotal = useMemo(
    () => dashboardScenarioOptions.reduce((total, scenario) => total + scenario.routeCount, 0),
    [dashboardScenarioOptions],
  );
  const kpis = useMemo(() => buildKpis(dashboardRoutes, dashboardRouteTotal), [dashboardRoutes, dashboardRouteTotal]);
  const jobsByScenario = useMemo(() => latestJobsByScenario(planningJobs), [planningJobs]);
  const isDriver = authSession?.role === "driver";
  const navItems = isDriver ? DRIVER_NAV_ITEMS : NAV_ITEMS;

  useEffect(() => {
    Promise.all([
      loadRoutes({ silent: true }),
      loadScenarios({ silent: true }),
      loadDrivers({ silent: true }),
      loadPlanningJobs({ silent: true }),
      loadConversations({ silent: true }),
    ]).catch(() => undefined);
  }, []);

  useEffect(() => {
    if (authSession?.role === "driver" && !["driverWorkspace", "driverProfile"].includes(activeView)) {
      setActiveView("driverWorkspace");
    }
    if (authSession?.role === "admin" && ["driverWorkspace", "driverProfile"].includes(activeView)) {
      setActiveView("dashboard");
    }
  }, [authSession?.role, activeView]);

  useEffect(() => {
    const hasRunningJob = planningJobs.some((job) => isRunningJob(job));
    if (!hasRunningJob) return undefined;
    const timer = window.setInterval(() => {
      setNow(Date.now());
      loadPlanningJobs({ silent: true, refreshRoutesOnCompletion: true }).catch(() => undefined);
    }, 2500);
    return () => window.clearInterval(timer);
  }, [planningJobs]);

  useEffect(() => {
    const hasRunningJob = planningJobs.some((job) => isRunningJob(job));
    if (!hasRunningJob) return undefined;
    const timer = window.setInterval(() => setNow(Date.now()), 1000);
    return () => window.clearInterval(timer);
  }, [planningJobs]);

  useEffect(() => {
    if (!currentPlan?.routes?.length) {
      setMapGeometry(null);
      return;
    }
    loadRouteGeometry(currentPlan, scenarioLocations).catch(() => undefined);
  }, [currentPlan?.scenario_id, JSON.stringify(currentPlan?.routes || []), JSON.stringify(Object.keys(scenarioLocations))]);

  useEffect(() => {
    if (authSession?.role !== "driver" || !authSession.driverId || !routes.length) return;
    const assignedRoute = routes.find((route) => route.driver_id === authSession.driverId);
    if (!assignedRoute) return;
    if (!selectedRoute || selectedRoute.driver_id !== authSession.driverId) {
      selectRoute(assignedRoute);
    }
    if (assignedRoute.scenario_id && selectedScenario?.id !== assignedRoute.scenario_id) {
      loadScenario(assignedRoute.scenario_id, { silent: true }).catch(() => undefined);
    }
  }, [authSession?.role, authSession?.driverId, routes.length, selectedRoute?.id, selectedScenario?.id]);

  useEffect(() => {
    if (authSession?.role !== "admin" || !activeDashboardScenarioId) return;
    if (selectedScenario?.id !== activeDashboardScenarioId) {
      loadScenario(activeDashboardScenarioId, { silent: true }).catch(() => undefined);
    }
  }, [authSession?.role, activeDashboardScenarioId, selectedScenario?.id]);

  async function request(path, options = {}) {
    const response = await fetch(`${api}${path}`, {
      headers: {
        "Content-Type": "application/json",
        ...(options.headers || {}),
      },
      ...options,
    });
    const body = await response.json();
    if (!response.ok) {
      throw new Error(body?.detail || body?.error?.message || `HTTP ${response.status}`);
    }
    return body;
  }

  function updateForm(patch) {
    setForm((value) => ({ ...value, ...patch }));
  }

  function selectRoute(route) {
    setSelectedRoute(route);
    updateForm({
      routeId: route.id,
      driverId: route.driver_id,
      scenarioId: route.scenario_id,
      status: route.status,
    });
    if (route.scenario_id && selectedScenario?.id !== route.scenario_id) {
      loadScenario(route.scenario_id, { silent: true }).catch(() => undefined);
    }
  }

  function toggleDashboardRoute(route) {
    selectRoute(route);
    setSelectedRouteIds((value) => {
      const scenarioRouteIds = dashboardRoutes.map((item) => item.id);
      const currentIds = Array.isArray(value) ? value : scenarioRouteIds;
      if (currentIds.includes(route.id)) {
        return currentIds.filter((routeId) => routeId !== route.id);
      }
      return [...currentIds, route.id];
    });
  }

  function selectDashboardScenario(scenarioId) {
    setDashboardScenarioId(scenarioId || null);
    setSelectedRouteIds(null);
    const firstRoute = routes.find((route) => route.scenario_id === scenarioId);
    if (firstRoute) {
      selectRoute(firstRoute);
    } else {
      setSelectedRoute(null);
      updateForm({ scenarioId: scenarioId || form.scenarioId });
      if (scenarioId) loadScenario(scenarioId, { silent: true }).catch(() => undefined);
    }
  }

  async function login({ username, password }) {
    try {
      setStatus({ text: "Signing in...", level: "info" });
      const normalizedUsername = username.trim().toLowerCase();
      const normalizedPassword = password.trim();
      if (normalizedUsername === "admin@adaptiveroute.com" && normalizedPassword === "12345678") {
        const session = {
          role: "admin",
          username: normalizedUsername,
          displayName: "Admin Console",
          createdAt: new Date().toISOString(),
        };
        persistSession(session);
        setAuthSession(session);
        setActiveView("dashboard");
        setStatus({ text: `Signed in as ${session.displayName}`, level: "ok" });
        return { ok: true };
      }

      const body = await request("/v1/driver-portal/login", {
        method: "POST",
        body: JSON.stringify({ username: username.trim(), password: normalizedPassword }),
      });
      const session = {
        role: "driver",
        username,
        displayName: body.driver?.name || body.driver?.id || username,
        driverId: body.driver?.id,
        createdAt: new Date().toISOString(),
      };
      persistSession(session);
      setDriverSession(body);
      setAuthSession(session);
      setDriverProfileForm({ capacity: String(body.driver?.capacity || ""), newPassword: "" });
      updateForm({
        driverId: body.driver?.id || form.driverId,
        loginUsername: username.trim(),
        loginPassword: normalizedPassword,
      });
      if (body.routes?.[0]) {
        selectRoute(body.routes[0]);
        await loadScenario(body.routes[0].scenario_id, { silent: true });
      }
      setActiveView("driverWorkspace");
      setStatus({ text: `Signed in as ${session.displayName}`, level: "ok" });
      return { ok: true };
    } catch (error) {
      setStatus({ text: `Login failed: ${error.message}`, level: "error" });
      return { ok: false, error: error.message };
    }
  }

  function logout() {
    window.localStorage.removeItem(AUTH_STORAGE_KEY);
    setAuthSession(null);
    setDriverSession(null);
    setActiveView("dashboard");
    setStatus({ text: "Signed out.", level: "idle" });
  }

  async function healthCheck() {
    try {
      setStatus({ text: "Checking API health...", level: "info" });
      const body = await request("/health");
      setStatus({ text: `API ${body.status}`, level: "ok" });
    } catch (error) {
      setStatus({ text: `Error: ${error.message}`, level: "error" });
    }
  }

  async function seedDemoScenario() {
    try {
      setStatus({ text: "Seeding NYC demo scenario...", level: "info" });
      const body = await request("/v1/scenarios/demo", { method: "POST", body: JSON.stringify({}) });
      updateForm({ scenarioId: body.id });
      setSelectedScenario(withLocationMetadata(body));
      await loadScenarios({ silent: true });
      setStatus({ text: `Scenario ready: ${body.id}`, level: "ok" });
    } catch (error) {
      setStatus({ text: `Error: ${error.message}`, level: "error" });
    }
  }

  async function importDailyOrdersFeed(scenarioName) {
    try {
      const scenarioPayload = buildDailyOrdersScenario(scenarioName);
      setStatus({ text: "Importing daily orders and calculating road distances...", level: "info" });
      const body = await request("/v1/scenarios/from-orders", {
        method: "POST",
        body: JSON.stringify(scenarioPayload),
      });
      updateForm({ scenarioId: body.id });
      setSelectedScenario(withLocationMetadata(body));
      setSelectedRoute(null);
      setSelectedRouteIds(null);
      setDashboardScenarioId(body.id);
      setMapGeometry(null);
      await loadScenarios({ silent: true });
      setStatus({ text: `${scenarioDisplayName(body)} ready · ${body.customers?.length || 0} stops`, level: "ok" });
    } catch (error) {
      setStatus({ text: `Error: ${error.message}`, level: "error" });
    }
  }

  async function uploadOrdersSpreadsheet(file, scenarioName) {
    try {
      if (!file) throw new Error("Select a CSV or XLSX file first.");
      setStatus({ text: "Uploading orders and calculating distance matrix...", level: "info" });
      const formData = new FormData();
      formData.append("file", file);
      formData.append("scenario_id", buildUploadedScenarioId(scenarioName || form.scenarioId));
      formData.append("depot_address", DEMO_LOCATIONS.D0.address);
      formData.append("depot_lat", String(DEMO_LOCATIONS.D0.lat));
      formData.append("depot_lng", String(DEMO_LOCATIONS.D0.lng));
      formData.append("vehicle_count", "2");
      formData.append("vehicle_capacity", form.capacity || "20");
      formData.append("use_road_distance", "true");

      const response = await fetch(`${api}/v1/scenarios/from-orders-file`, {
        method: "POST",
        body: formData,
      });
      const body = await response.json();
      if (!response.ok) {
        throw new Error(body?.detail || `HTTP ${response.status}`);
      }
      updateForm({ scenarioId: body.id });
      setSelectedScenario(withLocationMetadata(body));
      setDashboardScenarioId(body.id);
      await loadScenarios({ silent: true });
      setStatus({ text: `Uploaded ${body.customers?.length || 0} orders into ${body.id}.`, level: "ok" });
    } catch (error) {
      setStatus({ text: `Error: ${error.message}`, level: "error" });
    }
  }

  async function createRoute() {
    try {
      const payload = {
        id: form.routeId.trim(),
        driver_id: form.driverId.trim(),
        scenario_id: form.scenarioId.trim(),
        status: form.status.trim() || "in_progress",
        metadata: {
          created_from: "react-control-tower",
          seed_area: "New York City",
          stop_locations: DEMO_LOCATIONS,
        },
      };
      if (!payload.id || !payload.driver_id || !payload.scenario_id) {
        throw new Error("Route ID, Driver ID and Scenario ID are required.");
      }
      setStatus({ text: `Creating route ${payload.id}...`, level: "info" });
      const body = await request("/v1/operational-routes", {
        method: "POST",
        body: JSON.stringify(payload),
      });
      selectRoute(body);
      await loadRoutes({ silent: true });
      setStatus({ text: `Route ready: ${body.id}`, level: "ok" });
    } catch (error) {
      setStatus({ text: `Error: ${error.message}`, level: "error" });
    }
  }

  async function createDriver() {
    try {
      const payload = {
        id: form.driverId.trim(),
        name: form.driverName.trim(),
        vehicle_id: form.vehicleId.trim(),
        capacity: Number(form.capacity || 20),
        status: form.driverStatus || "available",
        region: form.region.trim() || "NYC",
        shift_start: form.shiftStart || null,
        shift_end: form.shiftEnd || null,
        metadata: {
          created_from: "driver_wizard",
          username: form.username.trim(),
          temporary_password: form.password,
          auth_mode: "mock",
        },
      };
      if (!payload.id || !payload.name || !payload.vehicle_id || !payload.metadata.username) {
        throw new Error("Driver ID, name, vehicle ID and username are required.");
      }
      setStatus({ text: `Creating driver ${payload.id}...`, level: "info" });
      await request("/v1/drivers", { method: "POST", body: JSON.stringify(payload) });
      await loadDrivers({ silent: true });
      setStatus({ text: `Driver ready: ${payload.id}`, level: "ok" });
    } catch (error) {
      setStatus({ text: `Error: ${error.message}`, level: "error" });
    }
  }

  async function updateDriver() {
    try {
      const driverId = form.driverId.trim();
      const payload = {
        name: form.driverName.trim(),
        vehicle_id: form.vehicleId.trim(),
        capacity: Number(form.capacity || 20),
        status: form.driverStatus || "available",
        region: form.region.trim() || "NYC",
        shift_start: form.shiftStart || null,
        shift_end: form.shiftEnd || null,
        metadata: {
          username: form.username.trim(),
          temporary_password: form.password,
          auth_mode: "mock",
        },
      };
      if (!driverId || !payload.name || !payload.vehicle_id || !payload.metadata.username) {
        throw new Error("Driver ID, name, vehicle ID and username are required.");
      }
      setStatus({ text: `Updating driver ${driverId}...`, level: "info" });
      await request(`/v1/drivers/${encodeURIComponent(driverId)}`, {
        method: "PUT",
        body: JSON.stringify(payload),
      });
      await loadDrivers({ silent: true });
      setStatus({ text: `Driver updated: ${driverId}`, level: "ok" });
    } catch (error) {
      setStatus({ text: `Error: ${error.message}`, level: "error" });
    }
  }

  async function deleteDriver(driverId) {
    try {
      if (!driverId) throw new Error("Select a driver first.");
      setStatus({ text: `Deleting driver ${driverId}...`, level: "info" });
      await request(`/v1/drivers/${encodeURIComponent(driverId)}`, { method: "DELETE" });
      setDriverRecords((items) => items.filter((driver) => driver.id !== driverId));
      await loadRoutes({ silent: true });
      setStatus({ text: `Driver deleted: ${driverId}. Assigned routes kept as removed.`, level: "ok" });
    } catch (error) {
      setStatus({ text: `Error: ${error.message}`, level: "error" });
    }
  }

  function editDriver(driver) {
    updateForm({
      driverId: driver.id,
      driverName: driver.name || driver.id,
      vehicleId: driver.vehicle_id || "",
      capacity: String(driver.capacity || 20),
      region: driver.region || "NYC",
      driverStatus: driver.status || "available",
      shiftStart: driver.shift_start || "",
      shiftEnd: driver.shift_end || "",
      username: driver.metadata?.username || driver.id.toLowerCase().replaceAll("-", "."),
      password: "",
    });
  }

  async function loadRoutes(options = {}) {
    try {
      if (!options.silent) setStatus({ text: "Syncing operational routes...", level: "info" });
      const body = await request("/v1/operational-routes");
      setRoutes(body);
      const selectedStillExists = selectedRoute && body.some((route) => route.id === selectedRoute.id);
      if ((!selectedRoute || !selectedStillExists) && body.length) selectRoute(body[0]);
      if (!body.length) setSelectedRoute(null);
      setSelectedRouteIds((value) => {
        const availableIds = new Set(body.map((route) => route.id));
        if (value === null) return null;
        return value.filter((routeId) => availableIds.has(routeId));
      });
      if (!options.silent) setStatus({ text: `Synced ${body.length} route(s).`, level: "ok" });
    } catch (error) {
      setStatus({ text: `Error: ${error.message}`, level: "error" });
    }
  }

  async function loadScenarios(options = {}) {
    try {
      if (!options.silent) setStatus({ text: "Loading scenarios...", level: "info" });
      const body = await request("/v1/scenarios");
      setScenarios(body);
      if (!selectedScenario && body.length) setSelectedScenario(withLocationMetadata(body[0]));
      if (!options.silent) setStatus({ text: `Loaded ${body.length} scenario(s).`, level: "ok" });
    } catch (error) {
      setStatus({ text: `Error: ${error.message}`, level: "error" });
    }
  }

  async function loadDrivers(options = {}) {
    try {
      if (!options.silent) setStatus({ text: "Loading drivers...", level: "info" });
      const body = await request("/v1/drivers");
      setDriverRecords(body);
      if (!options.silent) setStatus({ text: `Loaded ${body.length} driver(s).`, level: "ok" });
    } catch (error) {
      setStatus({ text: `Error: ${error.message}`, level: "error" });
    }
  }

  async function loadPlanningJobs(options = {}) {
    try {
      const previousCompleted = new Set(planningJobs.filter((job) => job.status === "completed").map((job) => job.id));
      if (!options.silent) setStatus({ text: "Loading optimization jobs...", level: "info" });
      const body = await request("/v1/planning/jobs");
      setPlanningJobs(body);
      const newlyCompleted = body.some((job) => job.status === "completed" && !previousCompleted.has(job.id));
      if (options.refreshRoutesOnCompletion && newlyCompleted) {
        await Promise.all([loadRoutes({ silent: true }), loadDrivers({ silent: true })]);
      }
      if (!options.silent) setStatus({ text: `Loaded ${body.length} optimization job(s).`, level: "ok" });
      return body;
    } catch (error) {
      if (!options.silent) setStatus({ text: `Error: ${error.message}`, level: "error" });
      return [];
    }
  }

  async function startPlanningJob(scenarioId = form.scenarioId || "demo-cvrp-8") {
    try {
      setStatus({ text: `Starting optimization for ${scenarioId}...`, level: "info" });
      const body = await request("/v1/planning/jobs", {
        method: "POST",
        body: JSON.stringify({
          scenario_id: scenarioId,
          route_prefix: "ROUTE",
          include_demo_drivers: true,
        }),
      });
      setPlanningJobs((jobs) => [body, ...jobs.filter((job) => job.id !== body.id)]);
      setDashboardScenarioId(scenarioId);
      updateForm({ scenarioId });
      setStatus({ text: `Optimization job started: ${body.id}`, level: "ok" });
    } catch (error) {
      setStatus({ text: `Error: ${error.message}`, level: "error" });
    }
  }

  async function runDailyPlanning() {
    return startPlanningJob(form.scenarioId || "demo-cvrp-8");
  }

  async function cancelPlanningJob(jobId) {
    try {
      setStatus({ text: `Cancelling optimization ${jobId}...`, level: "info" });
      const body = await request(`/v1/planning/jobs/${encodeURIComponent(jobId)}/cancel`, { method: "POST", body: JSON.stringify({}) });
      setPlanningJobs((jobs) => jobs.map((job) => (job.id === body.id ? body : job)));
      setStatus({ text: `Optimization cancelled: ${jobId}`, level: "ok" });
    } catch (error) {
      setStatus({ text: `Error: ${error.message}`, level: "error" });
    }
  }

  async function deleteScenario(scenarioId) {
    try {
      if (!scenarioId || scenarioId === "demo-cvrp-8") throw new Error("Default demo scenario cannot be deleted.");
      setStatus({ text: `Deleting scenario ${scenarioId}...`, level: "info" });
      await request(`/v1/scenarios/${encodeURIComponent(scenarioId)}`, { method: "DELETE" });
      setScenarios((items) => items.filter((scenario) => scenario.id !== scenarioId));
      if (selectedScenario?.id === scenarioId) setSelectedScenario(null);
      setStatus({ text: `Scenario deleted: ${scenarioId}`, level: "ok" });
    } catch (error) {
      setStatus({ text: `Error: ${error.message}`, level: "error" });
    }
  }

  async function deletePlanningJob(jobId) {
    try {
      setStatus({ text: `Deleting optimization job ${jobId}...`, level: "info" });
      await request(`/v1/planning/jobs/${encodeURIComponent(jobId)}`, { method: "DELETE" });
      setPlanningJobs((jobs) => jobs.filter((job) => job.id !== jobId));
      setStatus({ text: `Optimization job deleted: ${jobId}`, level: "ok" });
    } catch (error) {
      setStatus({ text: `Error: ${error.message}`, level: "error" });
    }
  }

  function debugScenarioWithAi(scenario, job) {
    setActiveView("chat");
    updateForm({ scenarioId: scenario.id });
    setMessage(
      `Debug scenario ${scenario.id}. Current optimization status: ${job?.status || "not started"} / ${job?.stage || "no job"}. Explain operational risk, solver state, and recommended next action.`,
    );
  }

  async function driverPortalLogin() {
    try {
      setStatus({ text: "Authenticating driver...", level: "info" });
      const body = await request("/v1/driver-portal/login", {
        method: "POST",
        body: JSON.stringify({ username: form.loginUsername, password: form.loginPassword }),
      });
      setDriverSession(body);
      setStatus({ text: `Driver portal loaded: ${body.driver.id}`, level: "ok" });
    } catch (error) {
      setStatus({ text: `Error: ${error.message}`, level: "error" });
    }
  }

  async function updateDriverRouteStatus(routeId, routeStatus) {
    try {
      const route = routes.find((item) => item.id === routeId);
      const driver = route ? driverRecords.find((item) => item.id === route.driver_id) : null;
      const username = driver?.metadata?.username || form.loginUsername;
      const password = form.loginPassword;
      const token = driverSession?.access_token;
      if (!token && (!username || !password)) throw new Error("Driver credentials are not available for this preview action.");
      setStatus({ text: `Updating ${routeId}...`, level: "info" });
      await request(`/v1/driver-portal/routes/${encodeURIComponent(routeId)}/status`, {
        method: "POST",
        headers: token ? { Authorization: `Bearer ${token}` } : undefined,
        body: JSON.stringify({
          username: token ? undefined : username,
          password: token ? undefined : password,
          status: routeStatus,
        }),
      });
      if (driverSession) await driverPortalLogin();
      await loadRoutes({ silent: true });
      setStatus({ text: `Route ${routeId} updated.`, level: "ok" });
    } catch (error) {
      setStatus({ text: `Error: ${error.message}`, level: "error" });
    }
  }

  async function updateOwnDriverProfile({ capacity, newPassword }) {
    try {
      const username = form.loginUsername || authSession?.username;
      const password = form.loginPassword;
      const token = driverSession?.access_token;
      if (!token && (!username || !password)) throw new Error("Current driver credentials are not available. Sign in again.");
      const payload = {
        username: token ? undefined : username,
        password: token ? undefined : password,
        capacity: capacity === "" || capacity === undefined || capacity === null ? undefined : Number(capacity),
        new_password: newPassword?.trim() || undefined,
      };
      setStatus({ text: "Updating driver profile...", level: "info" });
      const body = await request("/v1/driver-portal/profile", {
        method: "PUT",
        headers: token ? { Authorization: `Bearer ${token}` } : undefined,
        body: JSON.stringify(payload),
      });
      setDriverRecords((items) => items.map((driver) => (driver.id === body.id ? body : driver)));
      setDriverSession((session) => (session ? { ...session, driver: body } : session));
      updateForm({
        capacity: String(body.capacity || ""),
        loginPassword: payload.new_password || form.loginPassword,
      });
      setDriverProfileForm({ capacity: String(body.capacity || ""), newPassword: "" });
      await loadDrivers({ silent: true });
      setStatus({ text: "Driver profile updated.", level: "ok" });
    } catch (error) {
      setStatus({ text: `Error: ${error.message}`, level: "error" });
    }
  }

  async function loadScenario(scenarioId, options = {}) {
    try {
      if (!options.silent) setStatus({ text: `Loading scenario ${scenarioId}...`, level: "info" });
      const body = await request(`/v1/scenarios/${encodeURIComponent(scenarioId)}`);
      setSelectedScenario(withLocationMetadata(body));
      updateForm({ scenarioId: body.id });
      if (!options.silent) setStatus({ text: `Scenario loaded: ${body.id}`, level: "ok" });
    } catch (error) {
      if (!options.silent) setStatus({ text: `Error: ${error.message}`, level: "error" });
    }
  }

  async function loadSelectedRoute() {
    const routeId = form.routeId.trim() || selectedRoute?.id;
    return loadRouteById(routeId);
  }

  async function loadRouteById(routeId, options = {}) {
    try {
      if (!routeId) throw new Error("Select or type a route id.");
      if (!options.silent) setStatus({ text: `Loading route ${routeId}...`, level: "info" });
      const body = await request(`/v1/operational-routes/${encodeURIComponent(routeId)}`);
      selectRoute(body);
      if (!options.silent) setStatus({ text: `Route loaded: ${body.id}`, level: "ok" });
      return body;
    } catch (error) {
      if (!options.silent) setStatus({ text: `Error: ${error.message}`, level: "error" });
      return null;
    }
  }

  async function replan(messageOverride = null) {
    try {
      const payloadMessage = (typeof messageOverride === "string" ? messageOverride : message).trim();
      if (!payloadMessage) throw new Error("Driver message is required.");
      setStatus({ text: "Agentic replanning in progress...", level: "info" });
      const body = await request("/v1/agentic/replan", {
        method: "POST",
        body: JSON.stringify({
          conversation_id: conversationId,
          message: payloadMessage,
          scenario_id: form.scenarioId || "demo-cvrp-8",
        }),
      });
      setConversationId(body.conversation_id);
      setAgenticResult(body.agentic_result);
      setContextWindow(body.context_window);
      if (body.operational_route) selectRoute(body.operational_route);
      await loadMessages(body.conversation_id, { silent: true });
      await loadConversations({ silent: true });
      await loadRoutes({ silent: true });
      setMessage("");
      setStatus({ text: `Agent completed. Conversation ${body.conversation_id.slice(0, 8)}`, level: "ok" });
    } catch (error) {
      setStatus({ text: `Error: ${error.message}`, level: "error" });
    }
  }

  async function sendFollowUp() {
    const routeId = extractRouteIdFromText(message) || selectedRoute?.id || "the route referenced above";
    const followUp = `Before I move on ${routeId}, confirm the route count, distance impact, and whether every active customer is still served.`;
    setMessage(followUp);
    await replan(followUp);
  }

  async function loadContext(targetConversationId = conversationId, options = {}) {
    if (!targetConversationId) return setStatus({ text: "Run a conversation first.", level: "warn" });
    try {
      if (!options.silent) setStatus({ text: "Loading context window...", level: "info" });
      const body = await request(`/v1/conversations/${targetConversationId}/context`);
      setContextWindow(body);
      if (!options.silent) setStatus({ text: "Context window loaded.", level: "ok" });
    } catch (error) {
      if (!options.silent) setStatus({ text: `Error: ${error.message}`, level: "error" });
    }
  }

  async function loadMessages(targetConversationId = conversationId, options = {}) {
    if (!targetConversationId) return setStatus({ text: "Run a conversation first.", level: "warn" });
    try {
      if (!options.silent) setStatus({ text: "Loading messages...", level: "info" });
      const body = await request(`/v1/conversations/${targetConversationId}/messages`);
      setMessages(body);
      if (!options.silent) setStatus({ text: "Messages loaded.", level: "ok" });
    } catch (error) {
      setStatus({ text: `Error: ${error.message}`, level: "error" });
    }
  }

  async function loadAgentRuns(targetConversationId = conversationId, options = {}) {
    if (!targetConversationId) return setStatus({ text: "Run a conversation first.", level: "warn" });
    try {
      if (!options.silent) setStatus({ text: "Loading agent execution history...", level: "info" });
      const body = await request(`/v1/conversations/${targetConversationId}/agent-runs`);
      const latestRun = body.at(-1);
      setAgenticResult(latestRun?.result || null);
      if (!options.silent) setStatus({ text: "Agent execution loaded.", level: "ok" });
      return body;
    } catch (error) {
      if (!options.silent) setStatus({ text: `Error: ${error.message}`, level: "error" });
      return [];
    }
  }

  async function loadConversations(options = {}) {
    try {
      if (!options.silent) setStatus({ text: "Loading conversations...", level: "info" });
      const body = await request("/v1/conversations");
      setConversations(body);
      if (!options.silent) setStatus({ text: `Loaded ${body.length} conversation(s).`, level: "ok" });
      return body;
    } catch (error) {
      if (!options.silent) setStatus({ text: `Error: ${error.message}`, level: "error" });
      return [];
    }
  }

  async function selectConversation(targetConversationId) {
    try {
      setConversationId(targetConversationId);
      setStatus({ text: `Loading conversation ${targetConversationId.slice(0, 8)}...`, level: "info" });
      const conversation = conversations.find((item) => item.id === targetConversationId);
      const routeId = conversation?.metadata?.route_id || extractRouteIdFromText(conversation?.title);
      await Promise.all([
        loadMessages(targetConversationId, { silent: true }),
        loadContext(targetConversationId, { silent: true }),
        loadAgentRuns(targetConversationId, { silent: true }),
        routeId ? loadRouteById(routeId, { silent: true }) : Promise.resolve(null),
      ]);
      setStatus({ text: `Conversation loaded: ${targetConversationId.slice(0, 8)}`, level: "ok" });
    } catch (error) {
      setStatus({ text: `Error: ${error.message}`, level: "error" });
    }
  }

  async function startNewConversation() {
    setConversationId(null);
    setMessages([]);
    setContextWindow(null);
    setAgenticResult(null);
    setSelectedRoute(null);
    setMapGeometry(null);
    setMessage("");
    setStatus({ text: "New route chat ready.", level: "ok" });
  }

  async function deleteConversation(targetConversationId) {
    if (!targetConversationId) return;
    const confirmed = window.confirm("Delete this conversation and its messages, context and agent trace?");
    if (!confirmed) return;
    try {
      setStatus({ text: `Deleting conversation ${targetConversationId.slice(0, 8)}...`, level: "info" });
      await request(`/v1/conversations/${targetConversationId}`, { method: "DELETE" });
      setConversations((items) => items.filter((conversation) => conversation.id !== targetConversationId));
      if (conversationId === targetConversationId) {
        setConversationId(null);
        setMessages([]);
        setContextWindow(null);
        setAgenticResult(null);
      }
      setStatus({ text: "Conversation deleted.", level: "ok" });
    } catch (error) {
      setStatus({ text: `Error: ${error.message}`, level: "error" });
    }
  }

  async function ingestRag() {
    try {
      setStatus({ text: "Ingesting documentation...", level: "info" });
      const body = await request("/v1/rag/ingest", {
        method: "POST",
        body: JSON.stringify({ paths: ["README.md", "docs"] }),
      });
      setRagOutput(body);
      setStatus({ text: `RAG indexed: ${body.document_count} docs, ${body.chunk_count} chunks.`, level: "ok" });
    } catch (error) {
      setStatus({ text: `Error: ${error.message}`, level: "error" });
    }
  }

  async function queryRag() {
    try {
      setStatus({ text: "Querying knowledge base...", level: "info" });
      const body = await request("/v1/rag/query", {
        method: "POST",
        body: JSON.stringify({
          query: message || "How does the routing policy model work?",
          limit: 5,
        }),
      });
      setRagOutput(body);
      setStatus({ text: `RAG returned ${body.results.length} result(s).`, level: "ok" });
    } catch (error) {
      setStatus({ text: `Error: ${error.message}`, level: "error" });
    }
  }

  async function loadRouteGeometry(plan, locations = scenarioLocations) {
    try {
      const body = await request("/v1/maps/route-geometry", {
        method: "POST",
        body: JSON.stringify({
          plan,
          locations,
          overview: "full",
        }),
      });
      setMapGeometry(body);
    } catch {
      setMapGeometry({
        source: "frontend-fallback",
        routes: buildRouteLines(plan, locations),
        warnings: ["Backend map geometry unavailable."],
      });
    }
  }

  const actions = {
    login,
    logout,
    healthCheck,
    seedDemoScenario,
    importDailyOrdersFeed,
    uploadOrdersSpreadsheet,
    createRoute,
    createDriver,
    updateDriver,
    deleteDriver,
    editDriver,
    loadRoutes,
    loadScenarios,
    loadDrivers,
    loadPlanningJobs,
    startPlanningJob,
    runDailyPlanning,
    cancelPlanningJob,
    deletePlanningJob,
    deleteScenario,
    debugScenarioWithAi,
    driverPortalLogin,
    updateDriverRouteStatus,
    updateOwnDriverProfile,
    loadScenario,
    loadSelectedRoute,
    loadRouteById,
    replan,
    sendFollowUp,
    loadContext,
    loadMessages,
    loadAgentRuns,
    loadConversations,
    selectConversation,
    startNewConversation,
    deleteConversation,
    ingestRag,
    queryRag,
  };

  if (!authSession) {
    return (
      <LoginView
        onLogin={login}
      />
    );
  }

  return (
    <div className="app-shell">
      <aside className="sidebar">
        <div className="brand">
          <div className="brand-mark"><Route size={26} /></div>
          <div>
            <strong>AdaptiveRoute</strong>
            <span>{authSession.role === "driver" ? "Driver Workspace" : "Admin Console"}</span>
          </div>
        </div>

        <nav className="nav">
          {navItems.map((item) => {
            const Icon = item.icon;
            return (
              <button
                type="button"
                key={item.id}
                className={activeView === item.id ? "active" : ""}
                onClick={() => setActiveView(item.id)}
              >
                <Icon size={18} /> {item.label}
              </button>
            );
          })}
        </nav>

        <div className="session-card">
          <span>{authSession.role}</span>
          <strong>{authSession.displayName}</strong>
          <button type="button" className="secondary" onClick={actions.logout}>
            <LogOut size={15} /> Logout
          </button>
        </div>
      </aside>

      <main className="workspace">
        <Topbar activeView={activeView} />

        {!isDriver && activeView === "dashboard" && (
          <DashboardView
            kpis={kpis}
            routes={dashboardRoutes}
            scenarioOptions={dashboardScenarioOptions}
            activeScenarioId={activeDashboardScenarioId}
            selectDashboardScenario={selectDashboardScenario}
            selectedRoute={selectedRoute}
            selectedRoutes={selectedDashboardRoutes}
            selectedRouteIds={selectedDashboardRouteIds}
            setActiveView={setActiveView}
            toggleRouteSelection={toggleDashboardRoute}
            currentPlan={currentPlan}
            mapGeometry={mapGeometry}
            locations={scenarioLocations}
            agenticResult={agenticResult}
            actions={actions}
          />
        )}

        {!isDriver && activeView === "chat" && (
          <ChatView
            form={form}
            message={message}
            setMessage={setMessage}
            actions={actions}
            selectedRoute={selectedRoute}
            conversations={conversations}
            conversationId={conversationId}
            agenticResult={agenticResult}
            contextWindow={contextWindow}
            messages={messages}
            mapGeometry={mapGeometry}
            locations={scenarioLocations}
          />
        )}

        {!isDriver && activeView === "scenarios" && (
          <ScenariosView
            scenarios={scenarios}
            selectedScenario={selectedScenario}
            jobsByScenario={jobsByScenario}
            actions={actions}
            currentScenarioId={form.scenarioId}
            now={now}
          />
        )}

        {!isDriver && activeView === "drivers" && (
          <DriversView
            drivers={drivers}
            routes={routes}
            form={form}
            updateForm={updateForm}
            actions={actions}
            selectRoute={selectRoute}
            authSession={authSession}
            driverSession={driverSession}
          />
        )}

        {!isDriver && activeView === "knowledge" && (
          <KnowledgeView
            ragOutput={ragOutput}
            contextWindow={contextWindow}
            messages={messages}
            actions={actions}
          />
        )}

        {isDriver && activeView === "driverWorkspace" && (
          <DriverChatView
            authSession={authSession}
            drivers={drivers}
            routes={routes}
            selectedRoute={selectedRoute}
            currentPlan={currentPlan}
            mapGeometry={mapGeometry}
            locations={scenarioLocations}
            message={message}
            setMessage={setMessage}
            messages={messages}
            conversationId={conversationId}
            contextWindow={contextWindow}
            agenticResult={agenticResult}
            actions={actions}
            selectRoute={selectRoute}
          />
        )}

        {isDriver && activeView === "driverProfile" && (
          <DriverProfileView
            authSession={authSession}
            drivers={drivers}
            routes={routes}
            profileForm={driverProfileForm}
            setProfileForm={setDriverProfileForm}
            actions={actions}
          />
        )}
      </main>
    </div>
  );
}

function LoginView({ onLogin }) {
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");

  async function submitLogin(event) {
    event.preventDefault();
    setError("");
    const result = await onLogin({ username, password });
    if (result?.ok === false) {
      setError(result.error || "Invalid credentials.");
    }
  }

  return (
    <main className="login-shell">
      <section className="login-card">
        <div className="login-brand">
          <div className="brand-mark"><Route size={28} /></div>
          <div>
            <span className="eyebrow">AdaptiveRoute</span>
            <h1>Operational route intelligence</h1>
          </div>
        </div>

        <form className="login-form" onSubmit={submitLogin}>
          <Field label="Email or username" value={username} onChange={setUsername} />
          <Field label="Password" type="password" value={password} onChange={setPassword} />
          {error && <div className="login-error">{error}</div>}
          <button className="primary" type="submit">
            <LogIn size={17} /> Sign in
          </button>
        </form>
      </section>
    </main>
  );
}

function Topbar({ activeView }) {
  const title = {
    dashboard: "Routes of the day",
    chat: "Route replanning chat",
    scenarios: "Scenario management",
    drivers: "Driver operations",
    driverPortal: "Driver route workspace",
    driverWorkspace: "Route assistant",
    driverProfile: "Driver profile",
    knowledge: "Memory and knowledge base",
  }[activeView];
  const subtitle = {
    dashboard: "Upload or seed demand, run the traditional solver, then monitor today’s assigned routes.",
    chat: "Talk to the route agent when a driver reports blocks, delays or delivery constraints.",
    scenarios: "",
    drivers: "Create driver logins and vehicle capacity records. Route assignment is handled by the solver.",
    driverPortal: "Driver login with visibility and updates limited to assigned routes.",
    driverWorkspace: "Review your route, monitor metrics and talk to the route agent.",
    driverProfile: "Update your password and vehicle capacity.",
    knowledge: "Inspect RAG, memory and context-window state used by the agents.",
  }[activeView];

  return (
    <header className="topbar">
      <div>
        <span className="eyebrow">AdaptiveRoute · {activeView}</span>
        <h1>{title}</h1>
        {subtitle && <p>{subtitle}</p>}
      </div>
    </header>
  );
}

function DashboardView({
  kpis,
  routes,
  scenarioOptions,
  activeScenarioId,
  selectDashboardScenario,
  selectedRoute,
  selectedRoutes,
  selectedRouteIds,
  setActiveView,
  toggleRouteSelection,
  currentPlan,
  mapGeometry,
  locations,
  agenticResult,
  actions,
}) {
  const selectedRouteRecords = selectedRoutes;
  const displayPlan = combinePlansForOperationalRoutes(selectedRouteRecords);
  const displayGeometry = selectedRouteRecords.length > 1 ? null : filterGeometryForPlan(mapGeometry, displayPlan);
  const selectedDriver = selectedRoute ? routeDriverDisplayName(selectedRoute) : "No driver route selected";
  const selectedVehicle = displayPlan?.routes?.length === 1
    ? displayPlan.routes[0]?.vehicle_id || selectedRoute?.metadata?.solver_vehicle_id || selectedRoute?.metadata?.vehicle_id
    : null;
  const selectedCountLabel = selectedRouteRecords.length === 1
    ? `${selectedRouteRecords[0].id} · ${routeDriverDisplayName(selectedRouteRecords[0])}`
    : `${selectedRouteRecords.length} driver routes selected`;

  return (
    <>
      <section className="admin-dashboard">
        <div className="dashboard-main">
          <div className="kpi-grid dashboard-kpis">
            {kpis.map((kpi) => <KpiCard key={kpi.label} {...kpi} />)}
          </div>

          <Panel
            title={selectedRouteRecords.length > 1 ? "Selected driver routes" : "Selected driver route"}
            subtitle={selectedRouteRecords.length ? selectedCountLabel : "Select one or more routes from the operations queue"}
            icon={<MapPinned />}
          >
            {selectedRouteRecords.length > 0 && (
              <div className="selected-route-strip">
                <div>
                  <span className="eyebrow">{selectedRouteRecords.length > 1 ? "Driver routes" : "Driver route"}</span>
                  <strong>{selectedRouteRecords.length > 1 ? `${selectedRouteRecords.length} selected` : selectedRouteRecords[0].id}</strong>
                  <small>
                    {selectedRouteRecords.length > 1
                      ? selectedRouteRecords.map((route) => route.id).join(", ")
                      : `${selectedDriver}${selectedVehicle ? ` · ${selectedVehicle}` : ""} · ${selectedRouteRecords[0].status}`}
                  </small>
                </div>
                <div>
                  <span>Total distance</span>
                  <strong>{formatNumber(displayPlan?.total_distance)}</strong>
                </div>
              </div>
            )}
            <RouteMap plan={displayPlan} route={selectedRoute} geometry={displayGeometry} locations={locations} />
          </Panel>
        </div>

        <div className="dashboard-side">
          <Panel title="Scenario selector" icon={<Layers3 />}>
            <DashboardScenarioSelector
              scenarios={scenarioOptions}
              activeScenarioId={activeScenarioId}
              onSelect={selectDashboardScenario}
            />
          </Panel>

          <Panel title="Driver route selector" subtitle={`${routes.length} route records · select one or more to inspect`} icon={<Navigation />}>
            <FleetBoard
              routes={routes}
              selectedRoute={selectedRoute}
              selectedRouteIds={selectedRouteIds || []}
              onSelect={toggleRouteSelection}
              pageSize={10}
            />
          </Panel>

          <Panel title="Incident snapshot" subtitle="Latest agentic route event" icon={<Radar />}>
            <IncidentSnapshot result={agenticResult} onOpenChat={() => setActiveView("chat")} />
          </Panel>
        </div>
      </section>
    </>
  );
}

function ChatView({
  form,
  message,
  setMessage,
  actions,
  selectedRoute,
  conversations,
  conversationId,
  agenticResult,
  contextWindow,
  messages,
  mapGeometry,
  locations,
}) {
  const chatMessages = messages;
  const conversationPager = usePagedSearch(
    conversations,
    (conversation) => [
      conversation.title,
      conversation.id,
      conversation.metadata?.route_id,
      conversation.metadata?.scenario_id,
      conversation.updated_at,
    ].filter(Boolean).join(" "),
  );
  const hasActiveRouteConversation = Boolean(conversationId || agenticResult || contextWindow);
  const generatedPlan = hasActiveRouteConversation
    ? extractGeneratedPlan(agenticResult) || selectedRoute?.current_plan || contextWindow?.last_plan || null
    : null;
  const displayPlan = filterPlanForOperationalRoute(generatedPlan, selectedRoute);
  const displayGeometry = filterGeometryForPlan(mapGeometry, displayPlan);
  const generatedValidation = extractGeneratedValidation(agenticResult);
  const inferredRouteId = extractRouteIdFromText(message) || agenticResult?.route_id || contextWindow?.last_plan?.route_id;

  return (
    <section className="chat-workspace">
      <aside className="chat-history-panel">
        <div className="chat-history-header">
          <div>
            <span className="eyebrow">Route conversations</span>
            <strong>History</strong>
          </div>
          <div className="history-actions">
            <button className="icon-button" title="Refresh conversations" onClick={() => actions.loadConversations()}>
              <RefreshCw size={15} />
            </button>
            <button className="icon-button" title="New conversation" onClick={actions.startNewConversation}>
              <MessageSquareText size={15} />
            </button>
          </div>
        </div>
        <div className="list-panel-controls">
          <ListToolbar
            value={conversationPager.query}
            onChange={conversationPager.setQuery}
            total={conversations.length}
            filtered={conversationPager.filtered.length}
            placeholder="Search conversations..."
          />
        </div>
        <div className="conversation-list">
          {conversationPager.pageItems.map((conversation) => (
            <div
              key={conversation.id}
              className={`conversation-item conversation-row ${conversation.id === conversationId ? "active" : ""}`}
            >
              <button
                type="button"
                className="conversation-select"
                onClick={() => actions.selectConversation(conversation.id)}
              >
                <strong>{conversation.title || `Conversation ${conversation.id.slice(0, 8)}`}</strong>
                <span>{conversation.metadata?.route_id || conversation.metadata?.scenario_id || "route chat"}</span>
                <small>{formatDateTime(conversation.updated_at)}</small>
              </button>
              <button
                type="button"
                className="conversation-delete"
                title="Delete conversation"
                onClick={(event) => {
                  event.stopPropagation();
                  actions.deleteConversation(conversation.id);
                }}
              >
                <Trash2 size={15} />
              </button>
            </div>
          ))}
          {!conversationPager.filtered.length && <p className="empty slim">No conversations found.</p>}
        </div>
        <PaginationControls
          page={conversationPager.page}
          pageCount={conversationPager.pageCount}
          total={conversationPager.filtered.length}
          pageSize={conversationPager.pageSize}
          onPageChange={conversationPager.setPage}
        />
      </aside>

      <main className="chat-main-panel">
        <header className="chat-thread-header">
          <div>
            <span className="eyebrow">AdaptiveRoute agent</span>
            <h2>Route operations chat</h2>
            <p>Write naturally. The agent extracts the route id, event and constraints from the message.</p>
          </div>
        </header>

        {displayPlan?.routes?.length > 0 && (
          <section className="chat-route-map-stage">
            <div className="chat-route-map-heading">
              <div>
                <span className="eyebrow">Route visualization</span>
                <strong>{selectedRoute?.id || inferredRouteId || "Generated route"}</strong>
              </div>
              <small>
                {selectedRoute?.metadata?.solver_vehicle_id
                  ? `Vehicle ${selectedRoute.metadata.solver_vehicle_id}`
                  : "Generated plan"}
              </small>
            </div>
            <RouteMap plan={displayPlan} route={selectedRoute} geometry={displayGeometry} locations={locations} />
          </section>
        )}

        <section className="messages-area">
          {!chatMessages.length && (
            <div className="empty-chat-state">
              <Bot size={34} />
              <h3>Start a route disruption conversation</h3>
              <p>Describe the route id and the incident. The orchestrator will extract the event, call specialized agents, validate the plan and update memory.</p>
            </div>
          )}
          {chatMessages.map((item) => (
            <ChatMessageBubble key={item.id} message={item} />
          ))}
        </section>

        <footer className="chat-composer">
          <div className="composer-context">
            <span>{inferredRouteId ? `Detected route: ${inferredRouteId}` : "No route id detected in the draft"}</span>
            <small>Example: “Replan ROUTE-001. C1 → C3 is blocked.”</small>
          </div>
          <textarea
            value={message}
            onChange={(event) => setMessage(event.target.value)}
            placeholder="Tell the route agent what happened. Example: Replan ROUTE-001. C1 to C3 is blocked because of an accident."
          />
          <div className="chat-composer-actions">
            <button className="primary" onClick={actions.replan}><Send size={16} /> Send</button>
            <button className="secondary" onClick={actions.sendFollowUp}>Follow-up</button>
          </div>
        </footer>
      </main>

      <aside className="chat-inspector-panel">
        <Panel title="Agent execution" subtitle={conversationId ? `Conversation ${conversationId.slice(0, 8)}` : "No run yet"} icon={<BrainCircuit />}>
          <Timeline trace={agenticResult?.trace || []} />
        </Panel>
        <Panel title="Generated route" subtitle="Plan output" icon={<Navigation />}>
          <GeneratedRoutePanel plan={displayPlan} validation={generatedValidation} result={agenticResult} />
        </Panel>
        <Panel title="Context window" subtitle="Rolling memory" icon={<Database />}>
          <div className="memory-summary">
            <strong>Summary</strong>
            <span>{contextWindow?.summary || "No context window loaded yet."}</span>
          </div>
          <div className="button-row">
            <button className="secondary" onClick={() => actions.loadContext()}>Refresh context</button>
            <button className="secondary" onClick={() => actions.loadMessages()}>Refresh messages</button>
          </div>
        </Panel>
      </aside>
    </section>
  );
}

function ScenariosView({ scenarios, selectedScenario, jobsByScenario, actions, currentScenarioId, now }) {
  const [wizardOpen, setWizardOpen] = useState(false);
  const [wizardStep, setWizardStep] = useState(1);
  const [ordersFile, setOrdersFile] = useState(null);
  const [scenarioName, setScenarioName] = useState("NYC Morning Dispatch");
  const scenarioPager = usePagedSearch(
    scenarios,
    (scenario) => [
      scenario.id,
      scenarioDisplayName(scenario),
      `${scenario.customers?.length || 0} stops`,
      `${scenario.vehicles?.length || 0} vehicles`,
      jobsByScenario[scenario.id]?.status,
      jobsByScenario[scenario.id]?.stage,
    ].filter(Boolean).join(" "),
  );
  const selectedCustomerCount = selectedScenario?.customers?.length || 0;
  const selectedVehicleCount = selectedScenario?.vehicles?.length || 0;

  async function importFeedAndAdvance() {
    await actions.importDailyOrdersFeed(scenarioName);
    setWizardStep(2);
  }

  async function uploadAndAdvance() {
    await actions.uploadOrdersSpreadsheet(ordersFile, scenarioName);
    setWizardStep(2);
  }

  return (
    <section className="scenario-page">
      <div className="scenario-primary">
        <div className="scenario-toolbar">
          <div>
            <span className="eyebrow">Scenario operations</span>
            <h2>Planning scenarios</h2>
          </div>
          <button className="primary create-scenario-button" onClick={() => setWizardOpen((value) => !value)}>
            {wizardOpen ? "Close wizard" : "Create scenario"}
          </button>
        </div>

        {wizardOpen && (
          <Panel title="Create scenario" subtitle="Wizard" icon={<UploadCloud />}>
            <div className="scenario-flow">
              {[
                ["01", "Import orders", "Integration or spreadsheet"],
                ["02", "Optimize routes", "Run solver and publish routes"],
              ].map(([number, label, detail], index) => (
                <button
                  type="button"
                  key={number}
                  className={`flow-step ${wizardStep === index + 1 ? "active" : wizardStep > index + 1 ? "done" : ""}`}
                  onClick={() => setWizardStep(index + 1)}
                >
                  <span>{number}</span>
                  <strong>{label}</strong>
                  <small>{detail}</small>
                </button>
              ))}
            </div>

            {wizardStep === 1 && (
              <div className="upload-card elevated">
                <Field
                  label="Scenario name"
                  value={scenarioName}
                  onChange={setScenarioName}
                  placeholder="Example: NYC Morning Dispatch"
                />
                <div className="source-choice-card integration-primary">
                  <Database size={22} />
                  <div>
                    <strong>Operational order integration</strong>
                  </div>
                  <button className="primary" onClick={importFeedAndAdvance}>
                    <Database size={16} /> Import orders
                  </button>
                </div>
                <label className="file-drop">
                  <UploadCloud size={24} />
                  <div>
                    <strong>{ordersFile?.name || "Drop or choose an orders file"}</strong>
                    <span>CSV/XLSX · delivery_lat, delivery_lng and weight are required</span>
                  </div>
                  <input
                    type="file"
                    accept=".csv,.xlsx"
                    onChange={(event) => setOrdersFile(event.target.files?.[0] || null)}
                  />
                </label>
                <div className="scenario-action-grid">
                  <button className="secondary" onClick={uploadAndAdvance}>
                    <UploadCloud size={16} /> Upload spreadsheet
                  </button>
                </div>
                <div className="schema-hint">
                  <strong>Supported columns</strong>
                  <span>order_id, pickup_address, pickup_lat, pickup_lng, delivery_address, delivery_lat, delivery_lng, weight, volume, priority</span>
                </div>
              </div>
            )}

            {wizardStep === 2 && (
              <div className="solver-launch-card">
                <div>
                  <strong>{currentScenarioId}</strong>
                  <small>{scenarioDisplayName(currentScenarioId)}</small>
                  <span>Ready to start Pyomo + HiGHS optimization. The job will keep running in the backend while the UI polls status.</span>
                </div>
                <button className="primary play-button" onClick={() => actions.startPlanningJob(currentScenarioId)}>
                  <Play size={16} /> Run solver
                </button>
              </div>
            )}
          </Panel>
        )}

        <Panel title="Scenario registry" subtitle={`${scenarios.length} scenario records`} icon={<Layers3 />}>
          <div className="button-row registry-actions">
            <button className="secondary" onClick={() => actions.loadScenarios()}>Refresh scenarios</button>
            <button className="secondary" onClick={() => actions.loadPlanningJobs()}>Refresh jobs</button>
          </div>
          <ListToolbar
            value={scenarioPager.query}
            onChange={scenarioPager.setQuery}
            total={scenarios.length}
            filtered={scenarioPager.filtered.length}
            placeholder="Search scenarios, status or stage..."
          />
          <div className="scenario-list compact">
            {scenarioPager.pageItems.map((scenario) => (
              <ScenarioCard
                key={scenario.id}
                scenario={scenario}
                job={jobsByScenario[scenario.id]}
                now={now}
                selected={scenario.id === currentScenarioId}
                onClick={() => actions.loadScenario(scenario.id)}
                onPlay={() => actions.startPlanningJob(scenario.id)}
                onCancel={(jobId) => actions.cancelPlanningJob(jobId)}
                onDelete={() => actions.deleteScenario(scenario.id)}
                onDebug={() => actions.debugScenarioWithAi(scenario, jobsByScenario[scenario.id])}
              />
            ))}
            {!scenarioPager.filtered.length && <p className="empty">No scenarios found. Upload demand or adjust search.</p>}
          </div>
          <PaginationControls
            page={scenarioPager.page}
            pageCount={scenarioPager.pageCount}
            total={scenarioPager.filtered.length}
            pageSize={scenarioPager.pageSize}
            onPageChange={scenarioPager.setPage}
          />
        </Panel>
      </div>

      <aside className="scenario-detail">
        <Panel
          title={selectedScenario ? scenarioDisplayName(selectedScenario) : "No scenario selected"}
          subtitle={`${selectedCustomerCount} stops · ${selectedVehicleCount} vehicles`}
          icon={<Settings2 />}
        >
          <ScenarioSummary scenario={selectedScenario} />
        </Panel>
      </aside>
    </section>
  );
}

function ScenarioCard({ scenario, job, now, selected, onClick, onPlay, onCancel, onDelete, onDebug }) {
  const stops = scenario.customers?.length || 0;
  const vehicles = scenario.vehicles?.length || 0;
  const blocked = scenario.blocked_arcs?.length || 0;
  const status = job?.status || "ready";
  const isRunning = isRunningJob(job);
  const displayName = scenarioDisplayName(scenario);
  return (
    <article
      className={`scenario-card ${selected ? "selected" : ""} ${isRunning ? "optimizing" : ""}`}
      onClick={onClick}
      role="button"
      tabIndex={0}
      onKeyDown={(event) => {
        if (event.key === "Enter" || event.key === " ") onClick();
      }}
    >
      <div className="scenario-card-main">
        <div className="scenario-title-row">
          <strong>{displayName}</strong>
          <span className={`status-pill ${status}`}>{status}</span>
        </div>
        {displayName !== scenario.id && <small>{scenario.id}</small>}
        <span>{stops} stops · {vehicles} vehicles</span>
        {job && (
          <div className="job-progress">
            <div><i style={{ width: `${job.progress || 0}%` }} /></div>
            <small>{job.progress || 0}% · {humanizeStage(job.stage)} · {formatElapsed(job.started_at || job.created_at, job.completed_at, now)}</small>
          </div>
        )}
      </div>
      <div className="scenario-badges">
        <small>{blocked} blocks</small>
        <small>{scenario.distance_matrix?.length || 0} arcs</small>
      </div>
      <div className="scenario-card-actions" onClick={(event) => event.stopPropagation()}>
        <button type="button" className="icon-button" title="Run solver" onClick={onPlay}><Play size={15} /></button>
        <button
          type="button"
          className="icon-button"
          title="Cancel optimization"
          disabled={!job || !isRunning}
          onClick={() => onCancel(job.id)}
        >
          <Square size={14} />
        </button>
        <button type="button" className="icon-button" title="Debug with AI" onClick={onDebug}><Bug size={15} /></button>
        <button type="button" className="icon-button danger" title="Delete scenario" disabled={scenario.id === "demo-cvrp-8"} onClick={onDelete}>
          <Trash2 size={15} />
        </button>
      </div>
    </article>
  );
}

function DriversView({ drivers, routes, form, updateForm, actions, selectRoute }) {
  const driverPager = usePagedSearch(
    drivers,
    (driver) => [
      driver.id,
      driver.name,
      driver.vehicle_id,
      driver.status,
      driver.region,
      driver.metadata?.username,
    ].filter(Boolean).join(" "),
  );
  const assignedCount = drivers.filter((driver) => driver.routes.length > 0).length;
  const availableCount = drivers.filter((driver) => driver.status === "available").length;

  return (
    <section className="drivers-page">
      <div className="driver-command">
        <div>
          <span className="eyebrow">Fleet access control</span>
          <h2>Driver users, vehicles and route visibility</h2>
          <p>Maintain driver accounts and vehicle capacity records. Route ownership remains solver-owned after scenario optimization.</p>
        </div>
        <div className="driver-command-stats">
          <span><strong>{drivers.length}</strong> drivers</span>
          <span><strong>{availableCount}</strong> available</span>
          <span><strong>{assignedCount}</strong> assigned</span>
        </div>
      </div>

      <div className="drivers-layout">
        <Panel title="Driver roster" subtitle="CRUD registry" icon={<Users />}>
          <ListToolbar
            value={driverPager.query}
            onChange={driverPager.setQuery}
            total={drivers.length}
            filtered={driverPager.filtered.length}
            placeholder="Search drivers, vehicle, status..."
          />
          <div className="driver-list-header">
            <span>Driver</span>
            <span>Vehicle</span>
            <span>Status</span>
            <span>Actions</span>
          </div>
        <div className="driver-grid">
          {driverPager.pageItems.map((driver) => (
            <article className="driver-card" key={driver.id}>
              <div className="driver-identity">
                <div className="driver-avatar">{initials(driver.name || driver.id)}</div>
                <div>
                  <strong>{driver.name || driver.id}</strong>
                  <span>{driver.id}</span>
                  <small>{driver.region || "NYC"} · {driver.shift_start || "—"}–{driver.shift_end || "—"}</small>
                </div>
              </div>
              <div className="driver-vehicle">
                <strong>{driver.vehicle_id || "Pending"}</strong>
                <span>Capacity {driver.capacity || "—"}</span>
              </div>
              <div className="driver-status-stack">
                <span className={`status-pill ${driver.status || "available"}`}>{driver.status || "available"}</span>
                <small>{driver.routes.length} assigned route(s)</small>
              </div>
              <div className="driver-actions">
                <button type="button" className="icon-button" title="Edit driver" onClick={() => actions.editDriver(driver)}>
                  <Settings2 size={15} />
                </button>
                <button
                  type="button"
                  className="icon-button danger"
                  title="Delete driver"
                  onClick={() => actions.deleteDriver(driver.id)}
                >
                  <Trash2 size={15} />
                </button>
              </div>
            </article>
          ))}
          {!driverPager.filtered.length && <p className="empty">No drivers found. Create a driver user or adjust search.</p>}
        </div>
        <PaginationControls
          page={driverPager.page}
          pageCount={driverPager.pageCount}
          total={driverPager.filtered.length}
          pageSize={driverPager.pageSize}
          onPageChange={driverPager.setPage}
        />
      </Panel>

        <div className="drivers-side">
          <DriverCreationWizard form={form} updateForm={updateForm} actions={actions} />
          <DriverAssignmentPanel routes={routes} selectRoute={selectRoute} actions={actions} />
        </div>
      </div>
    </section>
  );
}

function DriverCreationWizard({ form, updateForm, actions }) {
  const [step, setStep] = useState(1);
  const steps = [
    { id: 1, label: "Profile" },
    { id: 2, label: "Vehicle" },
    { id: 3, label: "Access" },
  ];

  async function submitDriver() {
    await actions.createDriver();
    setStep(3);
  }

  async function saveDriver() {
    await actions.updateDriver();
    setStep(3);
  }

  return (
    <Panel title="Driver profile wizard" subtitle="Create or edit driver user" icon={<Truck />}>
      <div className="wizard">
        <div className="wizard-steps">
          {steps.map((item) => (
            <button
              key={item.id}
              type="button"
              className={step === item.id ? "active" : step > item.id ? "done" : ""}
              onClick={() => setStep(item.id)}
            >
              <span>{item.id}</span>
              {item.label}
            </button>
          ))}
        </div>

        {step === 1 && (
          <div className="wizard-card">
            <h3>Driver profile</h3>
            <p>Create the driver as a platform user. Route ownership is assigned later by optimization.</p>
            <Field label="Driver ID" value={form.driverId} onChange={(driverId) => updateForm({ driverId })} />
            <Field label="Driver name" value={form.driverName} onChange={(driverName) => updateForm({ driverName })} />
            <div className="form-grid">
              <Field label="Region" value={form.region} onChange={(region) => updateForm({ region })} />
              <SelectField
                label="Status"
                value={form.driverStatus || "available"}
                onChange={(driverStatus) => updateForm({ driverStatus })}
                options={["available", "on_route", "off_duty", "inactive"]}
              />
            </div>
            <div className="wizard-preview">
              <span>Suggested role</span>
              <strong>Driver portal user · route-level permissions</strong>
            </div>
            <div className="button-row">
              <button className="primary" onClick={() => setStep(2)}>Continue</button>
            </div>
          </div>
        )}

        {step === 2 && (
          <div className="wizard-card">
            <h3>Vehicle and capacity</h3>
            <p>The solver uses this vehicle capacity when assigning stops and generating routes.</p>
            <div className="form-grid">
              <Field label="Vehicle ID" value={form.vehicleId} onChange={(vehicleId) => updateForm({ vehicleId })} />
              <Field label="Capacity" value={form.capacity} onChange={(capacity) => updateForm({ capacity })} />
              <Field label="Shift start" value={form.shiftStart} onChange={(shiftStart) => updateForm({ shiftStart })} />
              <Field label="Shift end" value={form.shiftEnd} onChange={(shiftEnd) => updateForm({ shiftEnd })} />
            </div>
            <div className="button-row">
              <button className="secondary" onClick={() => setStep(1)}>Back</button>
              <button className="primary" onClick={() => setStep(3)}>Review</button>
            </div>
          </div>
        )}

        {step === 3 && (
          <div className="wizard-card">
            <h3>Access and review</h3>
            <p>Create temporary login credentials for the driver portal. Production should hash passwords and issue signed tokens.</p>
            <div className="review-grid">
              <ReviewItem label="Driver" value={`${form.driverName} (${form.driverId})`} />
              <ReviewItem label="Vehicle" value={`${form.vehicleId} · cap ${form.capacity}`} />
              <ReviewItem label="Status" value={form.driverStatus || "available"} />
              <ReviewItem label="Username" value={form.username} />
              <ReviewItem label="Password" value={form.password} />
            </div>
            <div className="form-grid">
              <Field label="Username" value={form.username} onChange={(username) => updateForm({ username })} />
              <Field label="Temporary password" value={form.password} onChange={(password) => updateForm({ password })} />
            </div>
            <div className="button-row">
              <button className="secondary" onClick={() => setStep(2)}>Back</button>
              <button className="primary" onClick={submitDriver}>Create driver</button>
              <button className="secondary" onClick={saveDriver}>Save changes</button>
              <button className="secondary" onClick={() => actions.loadDrivers()}>Reload drivers</button>
            </div>
          </div>
        )}
      </div>
    </Panel>
  );
}

function DriverChatView({
  authSession,
  drivers,
  routes,
  selectedRoute,
  currentPlan,
  mapGeometry,
  locations,
  message,
  setMessage,
  messages,
  conversationId,
  contextWindow,
  agenticResult,
  actions,
  selectRoute,
}) {
  const driver = drivers.find((item) => item.id === authSession.driverId) || null;
  const assignedRoutes = routes.filter((route) => route.driver_id === authSession.driverId);
  const routeForView = selectedRoute && assignedRoutes.some((route) => route.id === selectedRoute.id)
    ? selectedRoute
    : assignedRoutes[0] || null;
  const generatedPlan = extractGeneratedPlan(agenticResult) || routeForView?.current_plan || currentPlan;
  const displayPlan = filterPlanForOperationalRoute(generatedPlan, routeForView);
  const displayGeometry = filterGeometryForPlan(mapGeometry, displayPlan);
  const generatedValidation = extractGeneratedValidation(agenticResult);
  const detectedRouteId = extractRouteIdFromText(message) || routeForView?.id;
  const routeMetrics = buildDriverRouteMetrics(routeForView, displayPlan, driver);
  const routeAction = routeForView ? driverRouteAction(routeForView.status) : null;

  async function sendDriverMessage() {
    if (!routeForView) return;
    selectRoute(routeForView);
    const draft = message.trim();
    const scopedMessage = extractRouteIdFromText(draft)
      ? draft
      : `For route ${routeForView.id}, ${draft}`;
    await actions.replan(scopedMessage);
  }

  return (
    <section className="driver-chat-page">
      <main className="driver-chat-main">
        <header className="chat-thread-header">
          <div>
            <span className="eyebrow">AdaptiveRoute agent</span>
            <h2>{routeForView ? routeForView.id : "No route assigned"}</h2>
            <p>{driver?.name || authSession.displayName} · report blocks, delays, unavailable customers or route questions.</p>
          </div>
          {routeAction && (
            <button
              type="button"
              className="primary"
              onClick={() => actions.updateDriverRouteStatus(routeForView.id, routeAction.nextStatus)}
            >
              {routeAction.label}
            </button>
          )}
        </header>

        {routeForView && (
          <section className="chat-route-map-stage">
            <div className="driver-route-metrics">
              {routeMetrics.map((metric) => (
                <div key={metric.label} className="driver-route-metric">
                  <span>{metric.label}</span>
                  <strong>{metric.value}</strong>
                  {metric.detail && <small>{metric.detail}</small>}
                </div>
              ))}
            </div>
            <div className="chat-route-map-heading">
              <div>
                <span className="eyebrow">Your route map</span>
                <strong>{routeForView.id}</strong>
              </div>
              <small>{routeForView.status}</small>
            </div>
            <RouteMap plan={displayPlan} route={routeForView} geometry={displayGeometry} locations={locations} />
          </section>
        )}

        <section className="messages-area">
          {!messages.length && (
            <div className="empty-chat-state">
              <Bot size={34} />
              <h3>Start a route conversation</h3>
              <p>Describe what happened on the road. You can write naturally; your assigned route is applied automatically.</p>
            </div>
          )}
          {messages.map((item) => (
            <ChatMessageBubble key={item.id} message={item} />
          ))}
        </section>

        <footer className="chat-composer">
          <div className="composer-context">
            <span>{detectedRouteId ? `Route scope: ${detectedRouteId}` : "No assigned route"}</span>
            <small>Example: “C3 to C5 is blocked by traffic. Should I replan?”</small>
          </div>
          <textarea
            value={message}
            onChange={(event) => setMessage(event.target.value)}
            placeholder="Tell the route agent what happened on your route."
            disabled={!routeForView}
          />
          <div className="chat-composer-actions">
            <button className="primary" disabled={!routeForView || !message.trim()} onClick={sendDriverMessage}>
              <Send size={16} /> Send
            </button>
            <button className="secondary" disabled={!conversationId} onClick={actions.sendFollowUp}>Follow-up</button>
          </div>
        </footer>
      </main>

      <aside className="driver-chat-side">
        <Panel title="Generated route" subtitle="Plan output" icon={<Navigation />}>
          <GeneratedRoutePanel plan={displayPlan} validation={generatedValidation} result={agenticResult} />
        </Panel>
        <Panel title="Context window" subtitle="Rolling memory" icon={<Database />}>
          <div className="memory-summary">
            <strong>Summary</strong>
            <span>{contextWindow?.summary || "No context window loaded yet."}</span>
          </div>
        </Panel>
      </aside>
    </section>
  );
}

function DriverProfileView({ authSession, drivers, routes, profileForm, setProfileForm, actions }) {
  const driver = drivers.find((item) => item.id === authSession.driverId) || null;
  const assignedRoutes = routes.filter((route) => route.driver_id === authSession.driverId);

  return (
    <section className="driver-profile-page">
      <Panel title="Driver account" subtitle="Profile settings" icon={<Settings2 />}>
        <div className="driver-profile-hero">
          <div className="driver-avatar large">{initials(driver?.name || authSession.displayName)}</div>
          <div>
            <span className="eyebrow">{driver?.id || authSession.driverId}</span>
            <h2>{driver?.name || authSession.displayName}</h2>
            <p>{driver?.vehicle_id || "Vehicle pending"} · {driver?.region || "Assigned operations"} · {assignedRoutes.length} route(s)</p>
          </div>
        </div>
        <div className="driver-profile-form wide">
          <Field
            label="Vehicle capacity"
            value={profileForm.capacity}
            onChange={(capacity) => setProfileForm((value) => ({ ...value, capacity }))}
          />
          <Field
            label="New password"
            type="password"
            value={profileForm.newPassword}
            onChange={(newPassword) => setProfileForm((value) => ({ ...value, newPassword }))}
          />
          <button
            type="button"
            className="primary"
            onClick={() => actions.updateOwnDriverProfile(profileForm)}
          >
            Save profile
          </button>
        </div>
      </Panel>
    </section>
  );
}

function driverRouteAction(status) {
  if (status === "assigned") {
    return { label: "Start route", nextStatus: "in_progress" };
  }
  if (status === "in_progress") {
    return { label: "Complete route", nextStatus: "completed" };
  }
  return null;
}

function buildDriverRouteMetrics(route, plan, driver) {
  const vehicleRoute = plan?.routes?.[0] || {};
  const stops = Array.isArray(vehicleRoute.stops) ? vehicleRoute.stops : [];
  const deliveryStops = stops.filter((stop) => stop !== "D0");
  const load = Number(vehicleRoute.load ?? 0);
  const capacity = Number(driver?.capacity ?? route?.metadata?.driver?.capacity ?? 0);
  const slack = capacity ? capacity - load : null;
  return [
    {
      label: "Status",
      value: route?.status || "—",
      detail: route?.metadata?.solver_vehicle_id ? `Vehicle ${route.metadata.solver_vehicle_id}` : undefined,
    },
    {
      label: "Next stop",
      value: deliveryStops[0] || "—",
      detail: deliveryStops.length ? `${deliveryStops.length} delivery stops` : "No delivery stops",
    },
    {
      label: "Distance",
      value: formatNumber(plan?.total_distance ?? vehicleRoute.distance),
      detail: "route-distance units",
    },
    {
      label: "Load",
      value: capacity ? `${load}/${capacity}` : formatNumber(load),
      detail: slack === null ? "capacity unavailable" : `${slack} capacity slack`,
    },
    {
      label: "Sequence",
      value: stops.length ? stops.join(" → ") : "—",
      detail: scenarioDisplayName(route?.scenario_id),
    },
  ];
}

function DriverAssignmentPanel({ routes, selectRoute, actions }) {
  return (
    <Panel title="Solver assignments" subtitle="Read-only route ownership" icon={<Route />}>
      <div className="wizard-note">
        <strong>Route assignment is optimization-owned.</strong>
        <span>Run scenario optimization to associate planned routes with available vehicles and drivers.</span>
      </div>
      <div className="button-row">
        <button className="primary play-button" onClick={actions.runDailyPlanning}><Play size={16} /> Run solver</button>
        <button className="secondary" onClick={() => actions.loadRoutes()}><Radar size={16} /> Refresh</button>
      </div>
      <FleetBoard routes={routes} selectedRoute={null} onSelect={selectRoute} />
    </Panel>
  );
}

function ReviewItem({ label, value }) {
  return (
    <div className="review-item">
      <span>{label}</span>
      <strong>{value || "—"}</strong>
    </div>
  );
}

function KnowledgeView({ ragOutput, contextWindow, messages, actions }) {
  return (
    <section className="data-grid">
      <Panel title="Knowledge base" subtitle="RAG ingestion and retrieval" icon={<Database />}>
        <div className="button-row">
          <button className="primary" onClick={actions.ingestRag}>Ingest docs</button>
          <button className="secondary" onClick={actions.queryRag}>Query RAG</button>
        </div>
        <pre>{JSON.stringify(ragOutput ?? {}, null, 2)}</pre>
      </Panel>
      <JsonPanel title="Context window" value={contextWindow} />
      <JsonPanel title="Conversation messages" value={messages} />
    </section>
  );
}

function DriverPortalView({ form, updateForm, drivers, routes, selectedRoute, actions, selectRoute, authSession, driverSession }) {
  const sessionDriverId = authSession?.role === "driver" ? authSession.driverId : null;
  const visibleDriver = drivers.find((driver) => driver.id === (sessionDriverId || form.driverId))
    || driverSession?.driver
    || drivers[0]
    || null;
  const visibleRoutes = visibleDriver
    ? routes.filter((route) => route.driver_id === visibleDriver.id)
    : [];
  const routePager = usePagedSearch(
    visibleRoutes,
    (route) => [route.id, route.status, route.scenario_id, scenarioDisplayName(route.scenario_id), route.current_plan?.routes?.[0]?.stops?.join(" ")].filter(Boolean).join(" "),
  );
  const routeForChat = selectedRoute && visibleRoutes.some((route) => route.id === selectedRoute.id)
    ? selectedRoute
    : visibleRoutes[0] || null;
  const isDriverLogin = authSession?.role === "driver";

  return (
    <section className="driver-portal-page">
      <Panel title="Driver workspace" subtitle={isDriverLogin ? "Authenticated driver route access" : "Admin preview"} icon={<Truck />}>
        <div className="wizard-card">
          <p>{isDriverLogin ? "You can inspect and update only the routes assigned to your driver profile." : "Select a driver to preview route-level workspace visibility."}</p>
          <div className="form-grid">
            {isDriverLogin ? (
              <Field label="Driver" value={visibleDriver?.id || ""} onChange={() => undefined} />
            ) : (
              <SelectField
                label="Driver"
                value={visibleDriver?.id || ""}
                onChange={(driverId) => {
                  const driver = drivers.find((item) => item.id === driverId);
                  updateForm({
                    driverId,
                    driverName: driver?.name || driverId,
                    loginUsername: driver?.metadata?.username || "",
                    loginPassword: "",
                  });
                }}
                options={drivers.map((driver) => driver.id)}
              />
            )}
            <Field label="Portal mode" value={isDriverLogin ? "Driver authenticated" : "Admin preview"} onChange={() => undefined} />
          </div>
          {visibleDriver && (
            <div className="driver-preview-card">
              <div className="driver-avatar">{initials(visibleDriver.name || visibleDriver.id)}</div>
              <div>
                <strong>{visibleDriver.name}</strong>
                <span>{visibleDriver.vehicle_id} · {visibleDriver.region} · {visibleRoutes.length} route(s)</span>
              </div>
            </div>
          )}
        </div>
      </Panel>

      <Panel
        title="Assigned routes"
        subtitle={visibleDriver ? `${visibleDriver.name} · route-level visibility` : "No driver selected"}
        icon={<Navigation />}
      >
        {!visibleDriver && <p className="empty">Create or select a driver to preview the portal.</p>}
        {visibleDriver && (
          <>
            <ListToolbar
              value={routePager.query}
              onChange={routePager.setQuery}
              total={visibleRoutes.length}
              filtered={routePager.filtered.length}
              placeholder="Search assigned routes..."
            />
            <div className="fleet-list">
              {routePager.pageItems.map((route) => (
                <div className={`driver-route-card ${routeForChat?.id === route.id ? "selected" : ""}`} key={route.id}>
                  <div>
                    <strong>{route.id}</strong>
                    <small>{scenarioDisplayName(route.scenario_id)}</small>
                    <span>{route.current_plan?.routes?.[0]?.stops?.join(" → ") || "No plan"}</span>
                  </div>
                  <small>{route.status}</small>
                  <div className="button-row">
                    <button className="secondary" onClick={() => selectRoute(route)}>Open route</button>
                    <button className="secondary" onClick={() => actions.updateDriverRouteStatus(route.id, "in_progress")}>
                      Start
                    </button>
                    <button className="secondary" onClick={() => actions.updateDriverRouteStatus(route.id, "completed")}>
                      Complete
                    </button>
                  </div>
                </div>
              ))}
              {!routePager.filtered.length && <p className="empty">No assigned route found for this driver.</p>}
            </div>
            <PaginationControls
              page={routePager.page}
              pageCount={routePager.pageCount}
              total={routePager.filtered.length}
              pageSize={routePager.pageSize}
              onPageChange={routePager.setPage}
            />
          </>
        )}
      </Panel>

      <Panel
        title="Route chat scope"
        subtitle={routeForChat ? `${routeForChat.id} · ${visibleDriver?.name}` : "No route selected"}
        icon={<MessageSquareText />}
      >
        <div className="wizard-card">
          <p>The driver chat will be scoped to the selected route. For now, use the admin Route Chat with the route id injected in the message.</p>
          <div className="button-row">
            <button
              className="primary"
              disabled={!routeForChat}
              onClick={() => {
                if (!routeForChat) return;
                selectRoute(routeForChat);
                updateForm({ routeId: routeForChat.id, driverId: visibleDriver.id });
                actions.loadSelectedRoute();
              }}
            >
              <MessageSquareText size={16} /> Prepare route chat
            </button>
          </div>
        </div>
      </Panel>
    </section>
  );
}

function KpiCard({ label, value, detail, icon, tone }) {
  return (
    <article className={`kpi ${tone || ""}`}>
      <div className="kpi-icon">{icon}</div>
      <span>{label}</span>
      <strong>{value}</strong>
      <small>{detail}</small>
    </article>
  );
}

function Panel({ title, subtitle, icon, children, id }) {
  return (
    <article className="panel" id={id}>
      <header className="panel-header">
        <div>
          {subtitle && <span className="panel-subtitle">{subtitle}</span>}
          <h2>{title}</h2>
        </div>
        <div className="panel-icon">{React.cloneElement(icon, { size: 20 })}</div>
      </header>
      {children}
    </article>
  );
}

function Field({ label, value, onChange, type = "text", placeholder = "" }) {
  return (
    <label className="field">
      {label}
      <input type={type} value={value} placeholder={placeholder} onChange={(event) => onChange(event.target.value)} />
    </label>
  );
}

function SelectField({ label, value, onChange, options }) {
  return (
    <label className="field">
      {label}
      <select value={value} onChange={(event) => onChange(event.target.value)}>
        {options.map((option) => (
          <option key={option} value={option}>{option.replaceAll("_", " ")}</option>
        ))}
      </select>
    </label>
  );
}

function ListToolbar({ value, onChange, total, filtered, placeholder = "Search records..." }) {
  return (
    <div className="list-toolbar">
      <label className="list-search">
        <Search size={16} />
        <input value={value} onChange={(event) => onChange(event.target.value)} placeholder={placeholder} />
      </label>
      <span>{filtered} of {total}</span>
    </div>
  );
}

function PaginationControls({ page, pageCount, total, pageSize, onPageChange }) {
  if (total <= pageSize) return null;
  return (
    <div className="pagination-controls">
      <button className="secondary" disabled={page <= 1} onClick={() => onPageChange(page - 1)}>
        <ChevronLeft size={15} /> Prev
      </button>
      <span>Page {page} of {pageCount}</span>
      <button className="secondary" disabled={page >= pageCount} onClick={() => onPageChange(page + 1)}>
        Next <ChevronRight size={15} />
      </button>
    </div>
  );
}

function usePagedSearch(items, getSearchText, pageSize = PAGE_SIZE) {
  const [query, setQuery] = useState("");
  const [page, setPage] = useState(1);
  const filtered = useMemo(() => {
    const needle = query.trim().toLowerCase();
    if (!needle) return items;
    return items.filter((item) => getSearchText(item).toLowerCase().includes(needle));
  }, [items, query, getSearchText]);
  const pageCount = Math.max(1, Math.ceil(filtered.length / pageSize));
  const safePage = Math.min(page, pageCount);

  useEffect(() => {
    setPage(1);
  }, [query, items.length]);

  useEffect(() => {
    if (page !== safePage) setPage(safePage);
  }, [page, safePage]);

  return {
    query,
    setQuery,
    page: safePage,
    setPage,
    pageCount,
    filtered,
    pageItems: filtered.slice((safePage - 1) * pageSize, safePage * pageSize),
    pageSize,
  };
}

function SeedAddressList() {
  return (
    <div className="address-strip">
      {Object.entries(DEMO_LOCATIONS)
        .slice(0, 5)
        .map(([id, location]) => (
          <div key={id} className="address-chip">
            <strong>{id}</strong>
            <span>{location.label}</span>
          </div>
        ))}
    </div>
  );
}

function DashboardScenarioSelector({ scenarios, activeScenarioId, onSelect }) {
  const [query, setQuery] = useState("");
  const [selectedDate, setSelectedDate] = useState("");
  const filteredScenarios = useMemo(() => {
    const needle = query.trim().toLowerCase();
    return scenarios.filter((scenario) => {
      const timestamp = scenario.createdAt || scenario.updatedAt;
      const matchesDate = !selectedDate || formatDateInputValue(timestamp) === selectedDate;
      const haystack = [
        scenario.id,
        scenario.name,
        scenario.displayName,
        timestamp,
        formatDateTime(timestamp),
      ].filter(Boolean).join(" ").toLowerCase();
      return matchesDate && (!needle || haystack.includes(needle));
    });
  }, [scenarios, query, selectedDate]);
  const scenarioPager = usePagedSearch(filteredScenarios, (scenario) => scenario.id, 10);

  if (!scenarios.length) {
    return <p className="empty slim">No planned scenarios available yet.</p>;
  }

  return (
    <>
      <div className="scenario-selector-filters">
        <label className="list-search">
          <Search size={16} />
          <input
            value={query}
            onChange={(event) => setQuery(event.target.value)}
            placeholder="Search scenario name, id or date..."
          />
        </label>
        <input
          className="date-filter-input"
          type="date"
          value={selectedDate}
          onChange={(event) => setSelectedDate(event.target.value)}
        />
        {selectedDate && (
          <button type="button" className="secondary clear-date-button" onClick={() => setSelectedDate("")}>
            Clear
          </button>
        )}
        <span>{scenarioPager.filtered.length} of {scenarios.length}</span>
      </div>
      <div className="dashboard-scenario-list">
        {scenarioPager.pageItems.map((scenario) => (
          <button
            type="button"
            key={scenario.id}
            className={`dashboard-scenario-card ${scenario.id === activeScenarioId ? "selected" : ""}`}
            onClick={() => onSelect(scenario.id)}
          >
            <div>
              <strong>{scenario.displayName}</strong>
              <span>{scenario.routeCount} route(s) · {scenario.stopCount || "—"} stops</span>
              <small>{scenario.id}</small>
            </div>
            <small>{formatDateTime(scenario.createdAt || scenario.updatedAt)}</small>
          </button>
        ))}
        {!scenarioPager.filtered.length && <p className="empty slim">No scenarios match this search.</p>}
      </div>
      <PaginationControls
        page={scenarioPager.page}
        pageCount={scenarioPager.pageCount}
        total={scenarioPager.filtered.length}
        pageSize={scenarioPager.pageSize}
        onPageChange={scenarioPager.setPage}
      />
    </>
  );
}

function FleetBoard({ routes, selectedRoute, selectedRouteIds = [], onSelect, pageSize = PAGE_SIZE }) {
  const routePager = usePagedSearch(
    routes,
    (route) => [
      route.id,
      route.driver_id,
      routeDriverDisplayName(route),
      route.status,
      route.scenario_id,
      scenarioDisplayName(route.scenario_id),
      route.metadata?.solver_vehicle_id,
    ].filter(Boolean).join(" "),
    pageSize,
  );
  if (!routes.length) {
    return <p className="empty">No route plans available for this dashboard view.</p>;
  }
  return (
    <>
      <ListToolbar
        value={routePager.query}
        onChange={routePager.setQuery}
        total={routes.length}
        filtered={routePager.filtered.length}
        placeholder="Search routes, driver, status..."
      />
      <div className="fleet-list">
        {routePager.pageItems.map((route) => {
          const scopedPlan = filterPlanForOperationalRoute(route.current_plan, route);
          const scopedRoute = scopedPlan?.routes?.[0];
          const sequence = scopedRoute?.stops?.join(" → ");
          const vehicle = scopedRoute?.vehicle_id || route.metadata?.solver_vehicle_id || route.metadata?.vehicle_id;
          const isChecked = selectedRouteIds.includes(route.id);
          return (
            <button
              type="button"
              className={`fleet-card ${isChecked ? "selected" : ""} ${route.id === selectedRoute?.id ? "primary" : ""} ${isRemovedDriver(route.driver_id) ? "removed-driver" : ""}`}
              key={route.id}
              onClick={() => onSelect(route)}
              aria-pressed={isChecked}
            >
              <span className="route-select-check">{isChecked ? "✓" : "+"}</span>
              <div className="fleet-card-main">
                <strong>{route.id}</strong>
                <small>{routeDriverDisplayName(route)}{vehicle ? ` · ${vehicle}` : ""} · {route.status}</small>
                <small>{scenarioDisplayName(route.scenario_id)}</small>
                {sequence && <span className="fleet-card-sequence">{sequence}</span>}
              </div>
              <em>{formatNumber(scopedPlan?.total_distance)}</em>
            </button>
          );
        })}
        {!routePager.filtered.length && <p className="empty slim">No routes found.</p>}
      </div>
      <PaginationControls
        page={routePager.page}
        pageCount={routePager.pageCount}
        total={routePager.filtered.length}
        pageSize={routePager.pageSize}
        onPageChange={routePager.setPage}
      />
    </>
  );
}

function RouteMap({ plan, route, geometry, locations }) {
  const [recenterSignal, setRecenterSignal] = useState(0);
  const hasRoutes = Boolean(plan?.routes?.length);
  const routeLines = useMemo(() => normalizeMapGeometry(plan, geometry, locations), [plan, geometry, locations]);
  const points = useMemo(() => collectPlannedPoints(plan, locations), [plan, locations]);
  const blockedLegs = useMemo(() => (hasRoutes ? extractBlockedLegs(route, plan, locations) : []), [hasRoutes, route, plan, locations]);
  const mapPoints = hasRoutes ? points : [];
  const fitPoints = hasRoutes ? points : collectLocationPoints(locations);
  const fitKey = buildMapFitKey(plan, fitPoints);

  if (!fitPoints.length) {
    return (
      <div className="map-empty">
        <MapPinned size={42} />
        <strong>No map data available</strong>
        <span>Create or load a scenario to render it over a real map.</span>
      </div>
    );
  }

  return (
    <div className="real-map">
      <MapContainer center={[40.724, -73.997]} zoom={13} scrollWheelZoom className="leaflet-map">
        <TileLayer
          attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>'
          url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
        />
        <FitBounds points={fitPoints} fitKey={fitKey} recenterSignal={recenterSignal} />
        {routeLines.map((line, index) => (
          <Polyline
            key={`${line.vehicleId}-${index}`}
            positions={line.positions}
            pathOptions={{ color: ROUTE_COLORS[index % ROUTE_COLORS.length], weight: 6, opacity: 0.86 }}
          >
            <Tooltip sticky>{line.vehicleId} · {line.stops.join(" → ")}</Tooltip>
          </Polyline>
        ))}
        {blockedLegs.map((line, index) => (
          <Polyline
            key={`blocked-${index}`}
            positions={line}
            pathOptions={{ color: "#ff3860", weight: 5, opacity: 0.9, dashArray: "10 10" }}
          >
            <Tooltip sticky>Reported blocked road</Tooltip>
          </Polyline>
        ))}
        {mapPoints.map((point) => (
          <CircleMarker
            key={point.id}
            center={[point.lat, point.lng]}
            radius={point.type === "depot" ? 9 : 7}
            pathOptions={{
              color: point.type === "depot" ? "#2df59d" : "#27d6ff",
              fillColor: point.type === "depot" ? "#2df59d" : "#27d6ff",
              fillOpacity: 0.95,
              weight: 2,
            }}
          >
            <Tooltip direction="top" offset={[0, -8]} permanent>{point.id}</Tooltip>
            <Popup>
              <strong>{point.label}</strong>
              <br />
              {point.address}
            </Popup>
          </CircleMarker>
        ))}
      </MapContainer>
      <div className="map-legend">
        <span><i className="legend-depot" /> Depot</span>
        <span><i className="legend-stop" /> Stop</span>
        <span><i className="legend-block" /> Block</span>
        <span><i className="legend-route" /> {hasRoutes ? geometry?.source || "mixed" : "Routes hidden"}</span>
      </div>
      <button type="button" className="map-recenter-button" onClick={() => setRecenterSignal((value) => value + 1)}>
        <MapPinned size={15} /> Recenter
      </button>
    </div>
  );
}

function FitBounds({ points, fitKey, recenterSignal }) {
  const map = useMap();
  const lastFitRef = useRef("");
  const lastRecenterRef = useRef(-1);
  useEffect(() => {
    if (points.length < 2) return;
    const shouldFitPlan = fitKey && lastFitRef.current !== fitKey;
    const shouldRecenter = lastRecenterRef.current !== recenterSignal;
    if (!shouldFitPlan && !shouldRecenter) return;
    map.fitBounds(points.map((point) => [point.lat, point.lng]), { padding: [30, 30] });
    lastFitRef.current = fitKey;
    lastRecenterRef.current = recenterSignal;
  }, [map, points, fitKey, recenterSignal]);
  return null;
}

function PlanSummary({ plan }) {
  if (!plan?.routes?.length) return <p className="empty">No current plan selected.</p>;
  return (
    <div className="plan-stack">
      <div className="metric-row">
        <span><strong>{plan.routes.length}</strong> vehicles</span>
        <span><strong>{formatNumber(plan.total_distance)}</strong> distance</span>
        <span><strong>{scenarioDisplayName(plan.scenario_id)}</strong></span>
      </div>
      {plan.routes.map((route, index) => (
        <div className="plan-route" key={`${route.vehicle_id}-${index}`} style={{ "--route-color": ROUTE_COLORS[index % ROUTE_COLORS.length] }}>
          <div>
            <strong>{route.vehicle_id}</strong>
            <small>{Math.max(route.stops.length - 2, 0)} stops · load {route.load}</small>
          </div>
          <span>{route.stops.map((stop) => DEMO_LOCATIONS[stop]?.label || stop).join(" → ")}</span>
          <em>{formatNumber(route.distance)}</em>
        </div>
      ))}
    </div>
  );
}

function GeneratedRoutePanel({ plan, validation, result }) {
  if (!plan?.routes?.length) {
    return (
      <div className="generated-route-empty">
        <Navigation size={28} />
        <strong>No generated route yet</strong>
        <span>Ask the agent to replan or explain a route. The latest generated plan will appear here.</span>
      </div>
    );
  }

  const removedCustomers = result?.comparison?.removed_customers || result?.final_validation?.removed_customers || [];
  const distanceDelta = result?.comparison?.distance_delta;

  return (
    <div className="generated-route-panel">
      <div className="route-plan-summary">
        <div>
          <span>Routes</span>
          <strong>{plan.routes.length}</strong>
        </div>
        <div>
          <span>Total distance</span>
          <strong>{formatNumber(plan.total_distance)}</strong>
        </div>
        <div>
          <span>Validation</span>
          <strong className={validation?.passed === false ? "danger-text" : "success-text"}>
            {validation?.passed === undefined ? "—" : validation.passed ? "Passed" : "Failed"}
          </strong>
        </div>
      </div>

      {(distanceDelta !== undefined || removedCustomers.length > 0) && (
        <div className="route-impact-strip">
          <span>Distance delta: <strong>{formatNumber(distanceDelta)}</strong></span>
          <span>Removed customers: <strong>{removedCustomers.length ? removedCustomers.join(", ") : "None"}</strong></span>
        </div>
      )}

      <div className="generated-route-list">
        {plan.routes.map((route, index) => (
          <article className="generated-route-card" key={`${route.vehicle_id || "vehicle"}-${index}`}>
            <header>
              <div>
                <strong>{route.vehicle_id || `Vehicle ${index + 1}`}</strong>
                <span>{Math.max((route.stops || []).length - 2, 0)} stops · load {route.load ?? "—"}</span>
              </div>
              <em>{formatNumber(route.distance)}</em>
            </header>
            <div className="route-stop-chain">
              {(route.stops || []).map((stop, stopIndex) => (
                <React.Fragment key={`${route.vehicle_id}-${stop}-${stopIndex}`}>
                  <span className="stop-chip">{stop}</span>
                  {stopIndex < route.stops.length - 1 && <small>→</small>}
                </React.Fragment>
              ))}
            </div>
          </article>
        ))}
      </div>
    </div>
  );
}

function Timeline({ trace }) {
  if (!trace?.length) return <p className="empty">No agent run yet.</p>;
  return (
    <div className="timeline">
      {trace.map((item, index) => {
        const payload = item.payload || {};
        const failed = payload.passed === false || payload.succeeded === false;
        return (
          <div className={`timeline-item ${failed ? "failed" : "passed"}`} key={`${item.node}-${index}`}>
            <span>{index + 1}</span>
            <div>
              <strong>{item.node}</strong>
              <small>{compactPayload(payload)}</small>
            </div>
          </div>
        );
      })}
    </div>
  );
}

function ChatMessageBubble({ message }) {
  const role = message.role || "assistant";
  const isAssistant = role === "assistant";
  const isTool = role === "tool" || role === "system";
  return (
    <article className={`chat-message ${role} ${message.draft ? "draft" : ""}`}>
      <div className="chat-message-avatar">
        {isAssistant ? <Bot size={17} /> : isTool ? <Settings2 size={17} /> : <Users size={17} />}
      </div>
      <div className="chat-message-body">
        <header>
          <strong>{isAssistant ? "AdaptiveRoute Agent" : isTool ? role : "User"}</strong>
          <small>{message.draft ? "draft" : formatDateTime(message.created_at)}</small>
        </header>
        <p>{message.content}</p>
        {message.metadata && Object.keys(message.metadata).length > 0 && (
          <details className="message-metadata">
            <summary>metadata</summary>
            <pre>{JSON.stringify(message.metadata, null, 2)}</pre>
          </details>
        )}
      </div>
    </article>
  );
}

function IncidentSnapshot({ result, onOpenChat }) {
  const event = result?.event;
  if (!event) {
    return (
      <div className="incident-empty">
        <ShieldCheck size={30} />
        <strong>No active disruption</strong>
        <span>Use Route Chat to simulate a road block or driver incident.</span>
        <button className="secondary" onClick={onOpenChat}>Open chat</button>
      </div>
    );
  }
  return (
    <div className="incident-card">
      <strong>{event.type || "Operational event"}</strong>
      <span>{event.description || "Route event detected by agent."}</span>
      <small>source: {result?.source || "agentic workflow"}</small>
      <button className="primary" onClick={onOpenChat}>Review in chat</button>
    </div>
  );
}

function ScenarioSummary({ scenario }) {
  const nodes = scenario ? [scenario.depot, ...(scenario.customers || [])].filter(Boolean) : [];
  const nodePager = usePagedSearch(
    nodes,
    (node) => [node.id, node.label, node.address, node.demand, node.priority].filter(Boolean).join(" "),
  );
  if (!scenario) return <p className="empty">Select or seed a scenario.</p>;
  return (
    <div className="scenario-workspace">
      <div className="scenario-metrics">
        <div>
          <span>Stops</span>
          <strong>{scenario.customers?.length || 0}</strong>
        </div>
        <div>
          <span>Fleet</span>
          <strong>{scenario.vehicles?.length || 0}</strong>
        </div>
        <div>
          <span>Matrix arcs</span>
          <strong>{scenario.distance_matrix?.length || 0}</strong>
        </div>
        <div>
          <span>Blocked</span>
          <strong>{scenario.blocked_arcs?.length || 0}</strong>
        </div>
      </div>

      <div className="fleet-capacity-strip">
        {(scenario.vehicles || []).map((vehicle) => (
          <div key={vehicle.id}>
            <span>{vehicle.id}</span>
            <strong>{vehicle.capacity}</strong>
            <small>capacity</small>
          </div>
        ))}
        {!scenario.vehicles?.length && <span className="empty-inline">No vehicles configured</span>}
      </div>

      <div className="stop-table">
        <ListToolbar
          value={nodePager.query}
          onChange={nodePager.setQuery}
          total={nodes.length}
          filtered={nodePager.filtered.length}
          placeholder="Search stops..."
        />
        <div className="stop-row header">
          <span>ID</span>
          <span>Location</span>
          <span>Demand</span>
          <span>Priority</span>
        </div>
        {nodePager.pageItems.map((node) => (
          <div className="stop-row" key={node.id}>
            <strong>{node.id}</strong>
            <span>{node.label || DEMO_LOCATIONS[node.id]?.label || node.address || "Synthetic node"}</span>
            <span>{node.demand ?? "Depot"}</span>
            <span>{node.priority ?? "—"}</span>
          </div>
        ))}
      </div>
      <PaginationControls
        page={nodePager.page}
        pageCount={nodePager.pageCount}
        total={nodePager.filtered.length}
        pageSize={nodePager.pageSize}
        onPageChange={nodePager.setPage}
      />

      <details className="debug-details">
        <summary>Show scenario JSON</summary>
        <pre>{JSON.stringify(scenario ?? {}, null, 2)}</pre>
      </details>
    </div>
  );
}

function ConversationPreview({ messages, contextWindow }) {
  return (
    <div className="conversation-preview">
      <div className="memory-summary">
        <strong>Context summary</strong>
        <span>{contextWindow?.summary || "No context window loaded yet."}</span>
      </div>
      <div className="message-list">
        {messages.slice(-6).map((message) => (
          <div className={`message-bubble ${message.role}`} key={message.id}>
            <strong>{message.role}</strong>
            <span>{message.content}</span>
          </div>
        ))}
        {!messages.length && <p className="empty">No messages loaded yet.</p>}
      </div>
    </div>
  );
}

function JsonPanel({ title, value, compact = false }) {
  return (
    <article className={`panel json-panel ${compact ? "compact-json" : ""}`}>
      <header className="panel-header">
        <div>
          <span className="panel-subtitle">Debug visibility</span>
          <h2>{title}</h2>
        </div>
        <div className="panel-icon"><ShieldCheck size={20} /></div>
      </header>
      <pre>{JSON.stringify(value ?? {}, null, 2)}</pre>
    </article>
  );
}

function buildKpis(routes, totalLoadedRoutes = routes.length) {
  const activeRoutes = routes.filter((item) => ["assigned", "in_progress"].includes(item.status));
  const totalPlan = combinePlansForOperationalRoutes(routes);
  return [
    {
      label: "Routes today",
      value: activeRoutes.length || routes.length || "—",
      detail: totalLoadedRoutes === routes.length ? `${routes.length} records loaded` : `${routes.length} today · ${totalLoadedRoutes} total`,
      icon: <Truck size={20} />,
    },
    {
      label: "Planned distance",
      value: totalPlan?.routes?.length ? formatNumber(totalPlan.total_distance) : "—",
      detail: "Total scenario distance",
      icon: <Navigation size={20} />,
    },
  ];
}

function buildDashboardScenarioOptions(routes, scenarios) {
  const routesByScenario = new Map();
  for (const route of routes) {
    if (!route.scenario_id) continue;
    const current = routesByScenario.get(route.scenario_id) || {
      routeCount: 0,
      stopCount: 0,
      createdAt: route.created_at || route.updated_at || null,
      updatedAt: route.updated_at || route.created_at || null,
    };
    const routeStops = Math.max((filterPlanForOperationalRoute(route.current_plan, route)?.routes?.[0]?.stops?.length || 2) - 2, 0);
    current.routeCount += 1;
    current.stopCount += routeStops;
    current.createdAt = earlierTimestamp(current.createdAt, route.created_at || route.updated_at);
    current.updatedAt = laterTimestamp(current.updatedAt, route.updated_at || route.created_at);
    routesByScenario.set(route.scenario_id, current);
  }

  return scenarios
    .map((scenario) => {
      const routeStats = routesByScenario.get(scenario.id) || {};
      return {
        id: scenario.id,
        routeCount: routeStats.routeCount || 0,
        stopCount: scenario.customers?.length || routeStats.stopCount || 0,
        createdAt: routeStats.createdAt || routeStats.updatedAt || null,
        updatedAt: routeStats.updatedAt || routeStats.createdAt || null,
        displayName: scenarioDisplayName(scenario),
        scenario,
      };
    })
    .filter((item) => item.routeCount > 0)
    .sort((a, b) => new Date(b.updatedAt || b.createdAt || 0) - new Date(a.updatedAt || a.createdAt || 0));
}

function resolveDashboardScenarioId(requestedId, scenarioOptions) {
  if (requestedId && scenarioOptions.some((scenario) => scenario.id === requestedId)) return requestedId;
  const latestToday = scenarioOptions.find((scenario) => isSameLocalDate(scenario.createdAt || scenario.updatedAt, new Date()));
  return latestToday?.id || null;
}

function isTodayRoute(route) {
  const timestamp = route?.created_at || route?.updated_at;
  return isSameLocalDate(timestamp, new Date());
}

function isSameLocalDate(timestamp, targetDate) {
  if (!timestamp) return false;
  const date = new Date(timestamp);
  if (Number.isNaN(date.getTime())) return false;
  return (
    date.getFullYear() === targetDate.getFullYear() &&
    date.getMonth() === targetDate.getMonth() &&
    date.getDate() === targetDate.getDate()
  );
}

function earlierTimestamp(left, right) {
  if (!left) return right || null;
  if (!right) return left;
  return new Date(left) <= new Date(right) ? left : right;
}

function laterTimestamp(left, right) {
  if (!left) return right || null;
  if (!right) return left;
  return new Date(left) >= new Date(right) ? left : right;
}

function mergeDriversWithRoutes(driverRecords, routes) {
  const byDriver = new Map();
  for (const driver of driverRecords) {
    byDriver.set(driver.id, { ...driver, routes: [], active: driver.status === "on_route" });
  }
  for (const route of routes) {
    if (isRemovedDriver(route.driver_id)) continue;
    const driver = byDriver.get(route.driver_id) || {
      id: route.driver_id,
      name: route.driver_id,
      vehicle_id: route.metadata?.solver_vehicle_id,
      capacity: route.metadata?.driver?.capacity,
      status: "on_route",
      routes: [],
      active: false,
      metadata: {},
    };
    driver.routes.push(route);
    driver.active = driver.active || ["assigned", "in_progress"].includes(route.status);
    if (driver.active && driver.status === "available") driver.status = "on_route";
    byDriver.set(route.driver_id, driver);
  }
  return [...byDriver.values()].sort((a, b) => a.id.localeCompare(b.id));
}

function isRemovedDriver(driverId) {
  return String(driverId || "").startsWith("removed:");
}

function formatRouteDriver(route) {
  if (!isRemovedDriver(route.driver_id)) return route.driver_id;
  const removed = route.metadata?.removed_driver;
  return `removed · ${removed?.name || route.driver_id.replace("removed:", "")}`;
}

function routeDriverDisplayName(route) {
  return (
    route?.metadata?.driver?.name ||
    route?.metadata?.removed_driver?.name ||
    formatRouteDriver(route)
  );
}

function initials(value) {
  const parts = String(value || "")
    .trim()
    .split(/\s+/)
    .filter(Boolean);
  if (!parts.length) return "DR";
  if (parts.length === 1) return parts[0].slice(0, 2).toUpperCase();
  return `${parts[0][0]}${parts[parts.length - 1][0]}`.toUpperCase();
}

function latestJobsByScenario(jobs) {
  return [...jobs]
    .sort((a, b) => new Date(b.updated_at || 0) - new Date(a.updated_at || 0))
    .reduce((lookup, job) => {
      if (!lookup[job.scenario_id]) lookup[job.scenario_id] = job;
      return lookup;
    }, {});
}

function humanizeStage(stage) {
  return String(stage || "ready").replaceAll("_", " ");
}

function isRunningJob(job) {
  return ["queued", "running"].includes(String(job?.status || "").toLowerCase());
}

function formatElapsed(startedAt, completedAt, now = Date.now()) {
  if (!startedAt) return "not started";
  const start = new Date(startedAt).getTime();
  const end = completedAt ? new Date(completedAt).getTime() : now;
  if (!Number.isFinite(start) || !Number.isFinite(end)) return "elapsed unavailable";
  const seconds = Math.max(0, Math.floor((end - start) / 1000));
  const minutes = Math.floor(seconds / 60);
  const rest = seconds % 60;
  return `${minutes}:${String(rest).padStart(2, "0")} elapsed`;
}

function readStoredSession() {
  try {
    const raw = window.localStorage.getItem(AUTH_STORAGE_KEY);
    return raw ? JSON.parse(raw) : null;
  } catch {
    return null;
  }
}

function persistSession(session) {
  window.localStorage.setItem(AUTH_STORAGE_KEY, JSON.stringify(session));
}

function formatDateTime(value) {
  if (!value) return "—";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return "—";
  return date.toLocaleString(undefined, {
    month: "short",
    day: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
  });
}

function buildRouteLines(plan, locations = DEMO_LOCATIONS) {
  if (!plan?.routes) return [];
  return plan.routes
    .map((route) => ({
      vehicleId: route.vehicle_id,
      stops: route.stops,
      positions: route.stops
        .map((stop) => locations[stop])
        .filter(Boolean)
        .map((location) => [location.lat, location.lng]),
    }))
    .filter((line) => line.positions.length >= 2);
}

function normalizeMapGeometry(plan, geometry, locations = DEMO_LOCATIONS) {
  if (!plan?.routes?.length) return [];
  if (!geometry?.routes?.length) return buildRouteLines(plan, locations);
  return geometry.routes
    .map((route) => ({
      vehicleId: route.vehicle_id || route.vehicleId,
      stops: route.stops || [],
      positions: route.geometry || route.positions || [],
    }))
    .filter((line) => line.positions.length >= 2);
}

function collectPlannedPoints(plan, locations = DEMO_LOCATIONS) {
  const ids = [...new Set(plan?.routes?.flatMap((route) => route.stops) || [])];
  return ids.map((id) => ({ id, ...locations[id] })).filter((point) => point.lat && point.lng);
}

function collectLocationPoints(locations = DEMO_LOCATIONS) {
  return Object.entries(locations || {})
    .map(([id, location]) => ({ id, ...location }))
    .filter((point) => point.lat && point.lng);
}

function buildMapFitKey(plan, points) {
  const planKey = (plan?.routes || [])
    .map((route) => `${route.vehicle_id || ""}:${(route.stops || []).join(">")}`)
    .join("|");
  const pointKey = (points || [])
    .map((point) => `${point.id}:${Number(point.lat).toFixed(5)},${Number(point.lng).toFixed(5)}`)
    .join("|");
  return `${plan?.scenario_id || "scenario"}::${planKey || "no-routes"}::${pointKey}`;
}

function extractBlockedLegs(route, plan, locations = DEMO_LOCATIONS) {
  const scenarioBlocked = route?.metadata?.blocked_arcs || route?.metadata?.event?.blocked_arcs || [];
  const resultBlocked = plan?.blocked_arcs || [];
  const blocked = [...scenarioBlocked, ...resultBlocked];
  const normalized = blocked
    .map((arc) => [arc.from || arc[0], arc.to || arc[1]])
    .filter(([from, to]) => locations[from] && locations[to]);
  return normalized.map(([from, to]) => [
    [locations[from].lat, locations[from].lng],
    [locations[to].lat, locations[to].lng],
  ]);
}

function withLocationMetadata(scenario) {
  if (!scenario) return null;
  const fallback = buildScenarioLocations(scenario);
  return {
    ...scenario,
    depot: { ...scenario.depot, ...fallback[scenario.depot.id] },
    customers: scenario.customers.map((customer) => ({ ...customer, ...fallback[customer.id] })),
  };
}

function extractGeneratedPlan(result) {
  if (!result) return null;
  return (
    result.final_plan ||
    result.candidate?.plan ||
    result.route_plan ||
    result.plan ||
    result.operational_route?.current_plan ||
    null
  );
}

function extractGeneratedValidation(result) {
  if (!result) return null;
  return result.final_validation || result.candidate?.validation || result.validation || null;
}

function filterPlanForOperationalRoute(plan, operationalRoute) {
  if (!plan?.routes?.length || !operationalRoute) return plan;
  const solverVehicleId = operationalRoute.metadata?.solver_vehicle_id;
  const routeIndexVehicleId = inferVehicleIdFromRouteId(operationalRoute.id, plan);
  const routeVehicles = new Set([
    solverVehicleId,
    routeIndexVehicleId,
    operationalRoute.metadata?.vehicle_id,
    operationalRoute.metadata?.driver?.vehicle_id,
  ].filter(Boolean));
  if (!routeVehicles.size) return plan;
  const filteredRoutes = plan.routes.filter((route) => routeVehicles.has(route.vehicle_id));
  if (!filteredRoutes.length) return plan;
  return {
    ...plan,
    routes: filteredRoutes,
    total_distance: filteredRoutes.reduce((sum, route) => sum + Number(route.distance || 0), 0),
  };
}

function combinePlansForOperationalRoutes(routeRecords = []) {
  const selectedPlans = routeRecords
    .map((route) => filterPlanForOperationalRoute(route.current_plan, route))
    .filter((plan) => plan?.routes?.length);
  if (!selectedPlans.length) return null;
  const routes = selectedPlans.flatMap((plan) => plan.routes || []);
  return {
    scenario_id: routeRecords[0]?.scenario_id || selectedPlans[0]?.scenario_id,
    routes,
    total_distance: routes.reduce((sum, route) => sum + Number(route.distance || 0), 0),
    blocked_arcs: selectedPlans.flatMap((plan) => plan.blocked_arcs || []),
  };
}

function inferVehicleIdFromRouteId(routeId, plan) {
  const match = String(routeId || "").match(/(\d+)$/);
  const routes = plan?.routes || [];
  if (!match || !routes.length) return null;
  const index = Number(match[1]) - 1;
  if (Number.isInteger(index) && index >= 0 && index < routes.length) {
    return routes[index]?.vehicle_id || null;
  }
  return `V${Number(match[1])}`;
}

function filterGeometryForPlan(geometry, plan) {
  if (!geometry?.routes?.length || !plan?.routes?.length) return geometry;
  const vehicleIds = new Set(plan.routes.map((route) => route.vehicle_id).filter(Boolean));
  if (!vehicleIds.size) return geometry;
  return {
    ...geometry,
    routes: geometry.routes.filter((route) => vehicleIds.has(route.vehicle_id || route.vehicleId)),
  };
}

function extractRouteIdFromText(text) {
  const match = String(text || "").match(/\bROUTE-[A-Z0-9-]+\b/i);
  return match ? match[0].toUpperCase() : null;
}

function buildScenarioLocations(scenario) {
  if (!scenario) return DEMO_LOCATIONS;
  const nodes = [scenario.depot, ...(scenario.customers || [])].filter(Boolean);
  return nodes.reduce((locations, node) => {
    const demo = DEMO_LOCATIONS[node.id] || DAILY_LOCATION_LOOKUP[node.id] || {};
    locations[node.id] = {
      ...demo,
      label: demo.label || node.label || node.address || node.id,
      address: demo.address || node.address || node.label || node.id,
      lat: Number(demo.lat ?? node.lat ?? node.y),
      lng: Number(demo.lng ?? node.lng ?? node.x),
      type: node.id === scenario.depot?.id ? "depot" : "customer",
    };
    return locations;
  }, {});
}

function ensureRouteInMessage(text, routeId) {
  if (!routeId || !text) return text;
  const routePattern = new RegExp(`\\b${escapeRegExp(routeId)}\\b`, "i");
  return routePattern.test(text) ? text : `${text} Route ${routeId}.`;
}

function compactPayload(payload) {
  if (payload.status) return `status=${payload.status}`;
  if (payload.source) return `source=${payload.source}`;
  if (payload.passed !== undefined) return payload.passed ? "validation passed" : "validation failed";
  if (payload.confidence) return `confidence=${payload.confidence}`;
  if (payload.succeeded !== undefined) return payload.succeeded ? "succeeded" : "failed";
  return JSON.stringify(payload).slice(0, 100);
}

function formatNumber(value) {
  if (value === undefined || value === null || value === "") return "—";
  const numeric = Number(value);
  return Number.isFinite(numeric) ? numeric.toFixed(2) : String(value);
}

function scenarioDisplayName(value) {
  const id = typeof value === "string" ? value : value?.id;
  const stopCount = typeof value === "object" && value?.customers?.length ? value.customers.length : null;
  if (!id) return "No scenario";
  if (id === "demo-cvrp-8") return "Demo CVRP Scenario";
  const repeatedBlockMatch = id.match(/^(orders-nyc-demo)(?:-block-[a-z0-9]+-[a-z0-9]+)+$/i);
  if (repeatedBlockMatch) return "NYC Demo Disruption";
  const uploadMatch = id.match(/^(.+)-upload-(\d{14})-[a-z0-9]+$/i);
  if (uploadMatch) return `${titleizeScenarioSlug(uploadMatch[1])} · Uploaded orders`;
  const namedManifestMatch = id.match(/^(.+)-(\d+)-(\d{14})-[a-z0-9]+$/i);
  if (namedManifestMatch) return `${titleizeScenarioSlug(namedManifestMatch[1])} · ${namedManifestMatch[2]} orders`;
  const manifestMatch = id.match(/^nyc-route-plan-(\d+)-/i);
  if (manifestMatch) return `NYC Route Plan · ${manifestMatch[1]} orders`;
  const legacyManifestMatch = id.match(/^daily-nyc-manifest-(\d+)-/i);
  if (legacyManifestMatch) return `NYC Route Plan · ${legacyManifestMatch[1]} orders`;
  const orderMatch = id.match(/^orders[-_]/i);
  if (orderMatch) return stopCount ? `Uploaded Orders · ${stopCount} stops` : "Uploaded Orders";
  return id
    .split(/[-_]/)
    .filter(Boolean)
    .map((part) => part.charAt(0).toUpperCase() + part.slice(1))
    .join(" ");
}

function buildUploadedScenarioId(name) {
  const runId = new Date().toISOString().replace(/\D/g, "").slice(0, 14);
  const randomSuffix = Math.random().toString(36).slice(2, 6);
  const scenarioSlug = slugifyScenarioName(name) || "uploaded-orders";
  return `${scenarioSlug}-upload-${runId}-${randomSuffix}`;
}

function slugifyScenarioName(value) {
  return String(value || "")
    .trim()
    .toLowerCase()
    .normalize("NFD")
    .replace(/[\u0300-\u036f]/g, "")
    .replace(/[^a-z0-9]+/g, "-")
    .replace(/^-+|-+$/g, "")
    .slice(0, 48);
}

function titleizeScenarioSlug(value) {
  return String(value || "")
    .split("-")
    .filter(Boolean)
    .map((part) => {
      if (part.toLowerCase() === "nyc") return "NYC";
      return part.charAt(0).toUpperCase() + part.slice(1);
    })
    .join(" ");
}

function formatDateInputValue(value) {
  if (!value) return "";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return "";
  const year = date.getFullYear();
  const month = String(date.getMonth() + 1).padStart(2, "0");
  const day = String(date.getDate()).padStart(2, "0");
  return `${year}-${month}-${day}`;
}

function randomInt(min, max) {
  return Math.floor(Math.random() * (max - min + 1)) + min;
}

function clamp(value, min, max) {
  return Math.max(min, Math.min(max, value));
}

function escapeRegExp(value) {
  return value.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
}

createRoot(document.getElementById("root")).render(<App />);
