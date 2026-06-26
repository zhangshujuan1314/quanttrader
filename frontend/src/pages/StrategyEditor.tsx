import React, { useState, useEffect, lazy, Suspense } from "react";
import {
  Card, Row, Col, Select, Button, Input, InputNumber, message, Modal, Spin, Space, Table, Tag, Empty,
} from "antd";
import { PlayCircleOutlined, SaveOutlined, ExperimentOutlined, CodeOutlined, BarChartOutlined } from "@ant-design/icons";
import ReactECharts from "echarts-for-react";
import * as api from "../api/client";

// ponytail: Monaco lazy-loaded, falls back to textarea if network unavailable
const MonacoEditor = lazy(() => import("@monaco-editor/react"));

function CodeEditor({ value, onChange }: { value: string; onChange: (v: string) => void }) {
  const [monacoError, setMonacoError] = useState(false);
  if (monacoError) {
    return <Input.TextArea rows={18} value={value} onChange={e => onChange(e.target.value)}
      style={{ fontFamily: "monospace", fontSize: 13 }} placeholder="输入 Python 策略代码..." />;
  }
  return (
    <Suspense fallback={<div style={{ height: 400, background: "#1e1e1e", display: "flex", alignItems: "center", justifyContent: "center" }}><Spin /></div>}>
      <ErrorBoundary onError={() => setMonacoError(true)}>
        <MonacoEditor height="400px" language="python" theme="vs-dark" value={value}
          onChange={v => onChange(v || "")} loading={<div style={{ height: 400, background: "#1e1e1e", display: "flex", alignItems: "center", justifyContent: "center" }}><Spin tip="加载编辑器..." /></div>}
          options={{ fontSize: 13, minimap: { enabled: false }, scrollBeyondLastLine: false }} />
      </ErrorBoundary>
    </Suspense>
  );
}

class ErrorBoundary extends React.Component<{ children: React.ReactNode; onError?: () => void }> {
  state = { hasError: false };
  static getDerivedStateFromError() { return { hasError: true }; }
  componentDidCatch() { this.props.onError?.(); }
  render() {
    if (this.state.hasError) return <div style={{ padding: 40, textAlign: "center", color: "#999" }}>组件加载失败</div>;
    return this.props.children;
  }
}

export default function StrategyEditor() {
  const [templates, setTemplates] = useState<Record<string, any>>({});
  const [code, setCode] = useState("");
  const [strategyName, setStrategyName] = useState("我的策略");
  const [strategyParams, setStrategyParams] = useState<Record<string, number>>({});
  const [tsCode, setTsCode] = useState("000001.SZ");
  const [startDate, setStartDate] = useState("2022-01-01");
  const [endDate, setEndDate] = useState("2024-12-31");
  const [running, setRunning] = useState(false);
  const [result, setResult] = useState<any>(null);
  const [savedId, setSavedId] = useState<string | null>(null);
  const [showOptimize, setShowOptimize] = useState(false);
  const [optimizeMetric, setOptimizeMetric] = useState("sharpe_ratio");
  const [optimizing, setOptimizing] = useState(false);
  const [optimizeResult, setOptimizeResult] = useState<any>(null);

  useEffect(() => { api.getTemplates().then(setTemplates).catch(() => {}); }, []);

  const loadTemplate = (key: string) => {
    const tmpl = templates[key];
    if (tmpl) {
      setCode(tmpl.code);
      setStrategyName(tmpl.name);
      setStrategyParams(tmpl.params || {});
    }
  };

  const handleRun = async () => {
    if (!code.trim()) return message.warning("请先编写策略代码");
    setRunning(true); setResult(null);
    try {
      const res = await api.runBacktest({ strategy_code: code, strategy_params: strategyParams, ts_code: tsCode, start_date: startDate, end_date: endDate });
      setResult(res);
      if (res.status === "completed") message.success("回测完成！");
    } catch (e: any) { message.error(e?.response?.data?.detail || e?.message || "回测失败"); }
    finally { setRunning(false); }
  };

  const handleSave = async () => {
    if (!code.trim()) return message.warning("策略代码不能为空");
    try {
      const payload = { name: strategyName, code, params: strategyParams };
      const res = savedId ? await api.updateStrategy(savedId, payload) : await api.createStrategy(payload);
      if (res.id) { setSavedId(res.id); message.success("策略已保存"); }
    } catch { message.error("保存失败"); }
  };

  const handleOptimize = async () => {
    if (!code.trim()) return message.warning("请先编写策略代码");
    if (Object.keys(strategyParams).length === 0) return message.warning("策略没有可优化参数");
    setOptimizing(true); setOptimizeResult(null);
    try {
      const grid: Record<string, number[]> = {};
      for (const [k, v] of Object.entries(strategyParams)) {
        const base = Number(v);
        const candidates = [Math.max(1, Math.floor(base * 0.5)), base, Math.floor(base * 1.5), Math.floor(base * 2)];
        grid[k] = [...new Set(candidates.filter(x => x > 0))];
      }
      const res = await api.optimizeStrategy({ strategy_code: code, ts_code: tsCode, start_date: startDate, end_date: endDate, param_grid: grid, optimize_metric: optimizeMetric });
      setOptimizeResult(res);
      message.success(`最优参数: ${JSON.stringify(res.best_params)}`);
    } catch (e: any) { message.error(e?.response?.data?.detail || "优化失败"); }
    finally { setOptimizing(false); }
  };

  const chartOption = result?.equity_curve?.length ? {
    tooltip: { trigger: "axis" as const },
    grid: { left: "3%", right: "4%", bottom: "3%", containLabel: true },
    xAxis: { type: "category" as const, data: result.equity_curve.map((e: any) => e.date) },
    yAxis: { type: "value" as const, name: "资产 (¥)", axisLabel: { formatter: (v: number) => (v / 10000).toFixed(1) + "万" } },
    series: [{
      name: "资金曲线", type: "line", data: result.equity_curve.map((e: any) => e.value),
      smooth: true, symbol: "none", lineStyle: { color: "#1677ff", width: 2 },
      areaStyle: { color: { type: "linear", x: 0, y: 0, x2: 0, y2: 1, colorStops: [{ offset: 0, color: "rgba(22,119,255,0.25)" }, { offset: 1, color: "rgba(22,119,255,0.02)" }] } },
    }],
  } : null;

  const metricCards = result?.metrics ? [
    { title: "总收益率", value: result.metrics.total_return + "%", color: result.metrics.total_return > 0 ? "#52c41a" : "#ff4d4f" },
    { title: "年化收益", value: result.metrics.annual_return + "%" },
    { title: "最大回撤", value: result.metrics.max_drawdown + "%", color: "#ff4d4f" },
    { title: "夏普比率", value: (result.metrics.sharpe_ratio ?? 0).toFixed(2) },
    { title: "胜率", value: result.metrics.win_rate + "%" },
    { title: "交易次数", value: result.metrics.total_trades },
  ] : [];

  return (
    <div>
      <Row gutter={16}>
        <Col span={10}>
          <Card size="small" title="策略编辑器" extra={
            <Space wrap>
              <Select size="small" placeholder="模板" style={{ width: 110 }}
                onChange={loadTemplate}
                options={Object.entries(templates).map(([k, v]) => ({ label: (v as any).name, value: k }))} />
              <Input size="small" style={{ width: 100 }} value={strategyName} onChange={e => setStrategyName(e.target.value)} />
              <Button size="small" icon={<SaveOutlined />} onClick={handleSave}>保存</Button>
              <Button size="small" icon={<ExperimentOutlined />} onClick={() => setShowOptimize(true)}>优化</Button>
              <Button size="small" type="primary" icon={<PlayCircleOutlined />} onClick={handleRun} loading={running}>回测</Button>
            </Space>
          }>
            <CodeEditor value={code} onChange={setCode} />
          </Card>

          <Card size="small" title="回测参数" style={{ marginTop: 12 }}>
            <Row gutter={12}>
              <Col span={8}><div style={{ marginBottom: 4 }}>股票代码</div><Input value={tsCode} onChange={e => setTsCode(e.target.value)} placeholder="000001.SZ" /></Col>
              <Col span={8}><div style={{ marginBottom: 4 }}>开始</div><Input value={startDate} onChange={e => setStartDate(e.target.value)} /></Col>
              <Col span={8}><div style={{ marginBottom: 4 }}>结束</div><Input value={endDate} onChange={e => setEndDate(e.target.value)} /></Col>
            </Row>
            {Object.keys(strategyParams).length > 0 && (
              <div style={{ marginTop: 12 }}>
                <div style={{ marginBottom: 4, fontWeight: 500 }}>策略参数</div>
                <Space wrap>
                  {Object.entries(strategyParams).map(([k, v]) => (
                    <Space key={k} size={4}>
                      <span style={{ fontSize: 12, color: "#666" }}>{k}:</span>
                      <InputNumber size="small" style={{ width: 80 }} value={v}
                        onChange={val => setStrategyParams(p => ({ ...p, [k]: val ?? 0 }))} />
                    </Space>
                  ))}
                </Space>
              </div>
            )}
          </Card>
        </Col>

        <Col span={14}>
          <Card size="small" title="回测结果">
            {running ? <div style={{ textAlign: "center", padding: 80 }}><Spin size="large" tip="回测运行中..." /></div>
            : result ? <>
              <Row gutter={[12, 12]}>
                {metricCards.map((m, i) => (
                  <Col span={8} key={i}>
                    <Card size="small" styles={{ body: { padding: "10px 14px" } }}>
                      <div style={{ fontSize: 12, color: "#999" }}>{m.title}</div>
                      <div style={{ fontSize: 22, fontWeight: 700, color: (m as any).color || "#222", marginTop: 2 }}>{m.value}</div>
                    </Card>
                  </Col>
                ))}
              </Row>
              {chartOption && <ReactECharts option={chartOption} style={{ height: 260, marginTop: 16 }} />}
              {result.trades?.length > 0 && (
                <Table size="small" style={{ marginTop: 12 }} dataSource={result.trades} rowKey={(_, i) => String(i)} pagination={{ pageSize: 10, size: "small" }}
                  columns={[
                    { title: "日期", dataIndex: "date", width: 90 },
                    { title: "方向", dataIndex: "action", width: 50, render: (v: string) => <Tag color={v === "buy" ? "green" : "red"}>{v === "buy" ? "买入" : "卖出"}</Tag> },
                    { title: "价格", dataIndex: "price", width: 70 },
                    { title: "数量", dataIndex: "size", width: 55 },
                    { title: "盈亏", dataIndex: "pnl", width: 70, render: (v: number) => <span style={{ color: (v > 0 ? "#52c41a" : v < 0 ? "#ff4d4f" : "#999") }}>{v?.toFixed(2)}</span> },
                  ]} />
              )}
            </> : <div style={{ textAlign: "center", padding: 80, color: "#bbb" }}>
              <BarChartOutlined style={{ fontSize: 48 }} />
              <p style={{ marginTop: 16 }}>编写策略代码，点击「回测」查看结果</p>
            </div>}
          </Card>
        </Col>
      </Row>

      <Modal title="参数优化" open={showOptimize} onCancel={() => setShowOptimize(false)} width={700} footer={null} destroyOnClose>
        <Space direction="vertical" style={{ width: "100%" }} size="middle">
          <div>
            <div style={{ marginBottom: 4 }}>优化目标</div>
            <Select value={optimizeMetric} onChange={setOptimizeMetric} style={{ width: 180 }}
              options={[{ label: "夏普比率", value: "sharpe_ratio" }, { label: "总收益率", value: "total_return" }, { label: "胜率", value: "win_rate" }, { label: "卡尔玛比率", value: "calmar_ratio" }]} />
          </div>
          <div style={{ fontSize: 12, color: "#999" }}>当前参数: {JSON.stringify(strategyParams)} — 自动围绕当前值生成参数网格</div>
          <Button type="primary" icon={<ExperimentOutlined />} onClick={handleOptimize} loading={optimizing} block>开始优化</Button>
          {optimizeResult && (
            <Card size="small" title="优化结果">
              <Space wrap style={{ marginBottom: 8 }}>
                <Tag color="green">最优: {JSON.stringify(optimizeResult.best_params)}</Tag>
                <Tag>{optimizeResult.best_metric_name}: {optimizeResult.best_metric?.toFixed(3)}</Tag>
                <Tag>共 {optimizeResult.total_combinations} 组</Tag>
              </Space>
              <Table size="small" dataSource={optimizeResult.results?.filter((r: any) => r.metrics)} rowKey={(_, i) => String(i)} pagination={{ pageSize: 12, size: "small" }}
                columns={[
                  { title: "参数", render: (_: any, r: any) => JSON.stringify(r.params), width: 160 },
                  { title: "收益率%", render: (_: any, r: any) => r.metrics?.total_return, width: 75 },
                  { title: "夏普", render: (_: any, r: any) => r.metrics?.sharpe_ratio, width: 65 },
                  { title: "回撤%", render: (_: any, r: any) => r.metrics?.max_drawdown, width: 70 },
                  { title: "胜率%", render: (_: any, r: any) => r.metrics?.win_rate, width: 65 },
                ]} />
            </Card>
          )}
        </Space>
      </Modal>
    </div>
  );
}
