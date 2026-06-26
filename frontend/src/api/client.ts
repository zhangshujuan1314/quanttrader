import axios from "axios";

const api = axios.create({
  baseURL: "/api",
  timeout: 120000,
});

// ── Data ──

export async function searchSymbols(q: string) {
  const { data } = await api.get("/data/symbols", { params: { q } });
  return data;
}

export async function getKline(tsCode: string, start: string, end: string) {
  const { data } = await api.get("/data/kline", { params: { ts_code: tsCode, start, end } });
  return data;
}

// ── Strategy ──

export async function getTemplates() {
  const { data } = await api.get("/strategy/templates");
  return data;
}

export async function listStrategies() {
  const { data } = await api.get("/strategy/");
  return data;
}

export async function getStrategy(id: string) {
  const { data } = await api.get(`/strategy/${id}`);
  return data;
}

export async function createStrategy(payload: { name: string; description?: string; code: string; params?: any }) {
  const { data } = await api.post("/strategy/", payload);
  return data;
}

export async function updateStrategy(id: string, payload: any) {
  const { data } = await api.put(`/strategy/${id}`, payload);
  return data;
}

export async function deleteStrategy(id: string) {
  const { data } = await api.delete(`/strategy/${id}`);
  return data;
}

// ── Backtest ──

export interface BacktestRequest {
  strategy_id?: string;
  strategy_code?: string;
  strategy_params?: Record<string, any>;
  ts_code: string;
  start_date: string;
  end_date: string;
  initial_cash?: number;
}

export async function runBacktest(payload: BacktestRequest) {
  const { data } = await api.post("/backtest/run", payload);
  return data;
}

export async function listBacktestResults() {
  const { data } = await api.get("/backtest/results");
  return data;
}

export async function getBacktestResult(id: string) {
  const { data } = await api.get(`/backtest/results/${id}`);
  return data;
}

export async function optimizeStrategy(payload: {
  strategy_id?: string;
  strategy_code?: string;
  ts_code: string;
  start_date: string;
  end_date: string;
  param_grid: Record<string, number[]>;
  optimize_metric?: string;
}) {
  const { data } = await api.post("/backtest/optimize", payload);
  return data;
}

export async function compareBacktests(resultIds: string[]) {
  const { data } = await api.post("/backtest/compare", { result_ids: resultIds });
  return data;
}

// ── Trade ──

export async function getAccount() {
  const { data } = await api.get("/trade/account");
  return data;
}

export async function placeOrder(payload: {
  symbol: string; action: string; quantity: number; limit_price?: number | null;
}) {
  const { data } = await api.post("/trade/order", payload);
  return data;
}

export async function getRiskStatus() {
  const { data } = await api.get("/trade/risk/status");
  return data;
}

export async function runMonteCarlo(resultId: string, n = 500, method = "resample") {
  const { data } = await api.get(`/backtest/results/${resultId}/monte-carlo`, {
    params: { n_simulations: n, method },
  });
  return data;
}

export async function runStressTest(resultId: string) {
  const { data } = await api.get(`/backtest/results/${resultId}/stress-test`);
  return data;
}

// ── Auth ──

export async function login(username: string, password: string) {
  const { data } = await api.post("/auth/login", { username, password });
  if (data.access_token) localStorage.setItem("token", data.access_token);
  return data;
}

export async function register(username: string, password: string, email?: string) {
  const { data } = await api.post("/auth/register", { username, password, email });
  if (data.access_token) localStorage.setItem("token", data.access_token);
  return data;
}

export async function getMe() {
  const token = localStorage.getItem("token");
  const { data } = await api.get("/auth/me", {
    headers: token ? { Authorization: `Bearer ${token}` } : {},
  });
  return data;
}
