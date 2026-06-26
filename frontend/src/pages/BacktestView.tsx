import { useState, useEffect, useCallback } from "react";
import { Card, Table, Tag, Button, Drawer, Descriptions, Spin, message, Tabs, Row, Col, Empty } from "antd";
import { EyeOutlined, ReloadOutlined, ExperimentOutlined } from "@ant-design/icons";
import ReactECharts from "echarts-for-react";
import * as api from "../api/client";

export default function BacktestView() {
  const [results, setResults] = useState<any[]>([]);
  const [loading, setLoading] = useState(false);
  const [detail, setDetail] = useState<any>(null);
  const [showDrawer, setShowDrawer] = useState(false);
  const [mcResult, setMcResult] = useState<any>(null);
  const [mcLoading, setMcLoading] = useState(false);

  const load = useCallback(async () => {
    setLoading(true);
    try { setResults(await api.listBacktestResults()); }
    catch { message.error("加载失败"); }
    finally { setLoading(false); }
  }, []);

  useEffect(() => { load(); }, [load]);

  const viewDetail = async (id: string) => {
    try { setDetail(await api.getBacktestResult(id)); setMcResult(null); setShowDrawer(true); }
    catch { message.error("加载详情失败"); }
  };

  const runMonteCarlo = async (id: string) => {
    setMcLoading(true);
    try { setMcResult(await api.runMonteCarlo(id)); }
    catch { message.error("模拟失败"); }
    finally { setMcLoading(false); }
  };

  const chartOption = detail?.equity_curve?.length ? {
    tooltip: { trigger: "axis" as const },
    grid: { left: "3%", right: "4%", bottom: "3%", containLabel: true },
    xAxis: { type: "category" as const, data: detail.equity_curve.map((e: any) => e.date) },
    yAxis: { type: "value" as const, name: "资产", axisLabel: { formatter: (v: number) => (v / 10000).toFixed(1) + "万" } },
    series: [{
      type: "line", data: detail.equity_curve.map((e: any) => e.value),
      smooth: true, symbol: "none", lineStyle: { color: "#1677ff", width: 2 },
      areaStyle: { color: { type: "linear", x: 0, y: 0, x2: 0, y2: 1, colorStops: [{ offset: 0, color: "rgba(22,119,255,0.2)" }, { offset: 1, color: "rgba(22,119,255,0.02)" }] } },
    }],
  } : null;

  const mcHistogram = mcResult?.histogram?.length ? {
    tooltip: { trigger: "axis" as const },
    xAxis: { type: "category" as const, data: mcResult.histogram.map((h: any) => h.bin.toFixed(1)), name: "收益率 %" },
    yAxis: { type: "value" as const, name: "频次" },
    series: [{ type: "bar", data: mcResult.histogram.map((h: any) => h.count), itemStyle: { color: "#1677ff" }, barMaxWidth: 20 }],
  } : null;

  return (
    <div>
      <Card title="回测中心" extra={<Button icon={<ReloadOutlined />} onClick={load} loading={loading}>刷新</Button>}>
        <Table dataSource={results} rowKey="id" loading={loading} size="middle"
          locale={{ emptyText: <Empty description="暂无回测结果，去「策略工坊」跑一次回测" /> }}
          columns={[
            { title: "股票", dataIndex: "ts_code", width: 90 },
            { title: "总收益", dataIndex: "total_return", width: 85, render: (v: number) => <Tag color={v > 0 ? "green" : "red"}>{v}%</Tag> },
            { title: "年化", dataIndex: "annual_return", width: 80, render: (v: number) => v + "%" },
            { title: "回撤", dataIndex: "max_drawdown", width: 80, render: (v: number) => <span style={{ color: "#ff4d4f" }}>{v}%</span> },
            { title: "夏普", dataIndex: "sharpe_ratio", width: 65 },
            { title: "胜率", dataIndex: "win_rate", width: 65, render: (v: number) => v + "%" },
            { title: "交易", dataIndex: "total_trades", width: 55 },
            { title: "时间", dataIndex: "created_at", width: 90, render: (v: string) => v?.slice(0, 10) },
            { title: "", width: 45, render: (_: any, r: any) => <Button size="small" icon={<EyeOutlined />} onClick={() => viewDetail(r.id)} /> },
          ]}
          pagination={{ pageSize: 15, showSizeChanger: false }} />
      </Card>

      <Drawer title="回测详情" width={750} open={showDrawer} onClose={() => setShowDrawer(false)} destroyOnClose>
        {detail ? (
          <Tabs items={[
            {
              key: "overview", label: "概览",
              children: <>
                <Descriptions column={3} size="small" bordered>
                  <Descriptions.Item label="股票">{detail.ts_code}</Descriptions.Item>
                  <Descriptions.Item label="总收益">{detail.metrics?.total_return}%</Descriptions.Item>
                  <Descriptions.Item label="年化收益">{detail.metrics?.annual_return}%</Descriptions.Item>
                  <Descriptions.Item label="最大回撤">{detail.metrics?.max_drawdown}%</Descriptions.Item>
                  <Descriptions.Item label="夏普比率">{detail.metrics?.sharpe_ratio}</Descriptions.Item>
                  <Descriptions.Item label="胜率">{detail.metrics?.win_rate}%</Descriptions.Item>
                  <Descriptions.Item label="交易次数">{detail.metrics?.total_trades}</Descriptions.Item>
                </Descriptions>
                {chartOption && <ReactECharts option={chartOption} style={{ height: 280, marginTop: 16 }} />}
                {detail.trades?.length > 0 && (
                  <Table size="small" style={{ marginTop: 16 }} dataSource={detail.trades} rowKey={(_, i) => String(i)} pagination={{ pageSize: 15, size: "small" }}
                    columns={[
                      { title: "日期", dataIndex: "date", width: 90 },
                      { title: "方向", dataIndex: "action", width: 50, render: (v: string) => <Tag color={v === "buy" ? "green" : "red"}>{v === "buy" ? "买" : "卖"}</Tag> },
                      { title: "价格", dataIndex: "price", width: 70 },
                      { title: "数量", dataIndex: "size", width: 55 },
                      { title: "盈亏", dataIndex: "pnl", width: 70, render: (v: number) => <span style={{ color: (v > 0 ? "#52c41a" : v < 0 ? "#ff4d4f" : "#999") }}>{v?.toFixed(2)}</span> },
                    ]} />
                )}
              </>,
            },
            {
              key: "mc", label: "蒙特卡洛",
              children: <>
                <Button icon={<ExperimentOutlined />} loading={mcLoading}
                  onClick={() => runMonteCarlo(detail.id)} block style={{ marginBottom: 16 }}>
                  运行蒙特卡洛模拟 (500次)
                </Button>
                {mcResult ? (
                  <>
                    <Row gutter={[12, 8]}>
                      <Col span={8}><StatBlock title="原始收益" value={mcResult.original_return + "%"} /></Col>
                      <Col span={8}><StatBlock title="模拟均值" value={mcResult.mean_return + "%"} /></Col>
                      <Col span={8}><StatBlock title="亏损概率" value={mcResult.prob_loss + "%"} color={mcResult.prob_loss > 30 ? "#ff4d4f" : "#52c41a"} /></Col>
                      <Col span={8}><StatBlock title="P5 最差" value={mcResult.p5_return + "%"} color="#ff4d4f" /></Col>
                      <Col span={8}><StatBlock title="中位数" value={mcResult.median_return + "%"} /></Col>
                      <Col span={8}><StatBlock title="P95 最好" value={mcResult.p95_return + "%"} color="#52c41a" /></Col>
                    </Row>
                    {mcHistogram && <ReactECharts option={mcHistogram} style={{ height: 240, marginTop: 12 }} />}
                    <div style={{ marginTop: 8, fontSize: 12, color: "#999" }}>方法: {mcResult.method} · 模拟: {mcResult.simulations} 次</div>
                  </>
                ) : <div style={{ padding: 40, textAlign: "center", color: "#999" }}>点击按钮运行蒙特卡洛模拟，评估策略稳健性</div>}
              </>,
            },
          ]} />
        ) : <Spin />}
      </Drawer>
    </div>
  );
}

function StatBlock({ title, value, color }: { title: string; value: string; color?: string }) {
  return (
    <Card size="small" styles={{ body: { padding: "10px 14px" } }}>
      <div style={{ fontSize: 12, color: "#999" }}>{title}</div>
      <div style={{ fontSize: 20, fontWeight: 700, color: color || "#222", marginTop: 2 }}>{value}</div>
    </Card>
  );
}
