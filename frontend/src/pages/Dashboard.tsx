import { useState, useEffect } from "react";
import { Card, Row, Col, Statistic, Table, Tag, Button, Empty } from "antd";
import { LineChartOutlined, CodeOutlined, DatabaseOutlined, ThunderboltOutlined } from "@ant-design/icons";
import { useNavigate } from "react-router-dom";
import * as api from "../api/client";

export default function Dashboard() {
  const [strategies, setStrategies] = useState<any[]>([]);
  const [results, setResults] = useState<any[]>([]);
  const navigate = useNavigate();

  useEffect(() => {
    api.listStrategies().then(setStrategies).catch(() => {});
    api.listBacktestResults().then(setResults).catch(() => {});
  }, []);

  const quickCards = [
    { title: "策略数量", value: strategies.length, icon: <CodeOutlined />, path: "/strategy", color: "#1677ff" },
    { title: "回测次数", value: results.length, icon: <LineChartOutlined />, path: "/backtest", color: "#52c41a" },
    { title: "数据状态", value: "就绪", icon: <DatabaseOutlined />, path: "/data", color: "#722ed1" },
    { title: "交易模式", value: "模拟盘", icon: <ThunderboltOutlined />, path: "/trade", color: "#faad14" },
  ];

  return (
    <div>
      <h2 style={{ marginBottom: 24, fontWeight: 600 }}>量化智投</h2>

      <Row gutter={[16, 16]}>
        {quickCards.map((c, i) => (
          <Col span={6} key={i}>
            <Card hoverable onClick={() => navigate(c.path)} styles={{ body: { padding: "16px 20px" } }}>
              <Statistic title={c.title} value={c.value} prefix={c.icon} valueStyle={{ color: c.color }} />
            </Card>
          </Col>
        ))}
      </Row>

      <Row gutter={16} style={{ marginTop: 24 }}>
        <Col span={12}>
          <Card title="最近策略" extra={<Button size="small" type="link" onClick={() => navigate("/strategy")}>全部 →</Button>}>
            {strategies.length === 0 ? (
              <Empty image={Empty.PRESENTED_IMAGE_SIMPLE} description="还没有策略，去「策略工坊」创建第一个" />
            ) : strategies.slice(0, 6).map((s: any) => (
              <div key={s.id} style={{ padding: "8px 0", borderBottom: "1px solid #f0f0f0", display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                <span><strong>{s.name}</strong></span>
                <span style={{ color: "#999", fontSize: 12 }}>{s.updated_at?.slice(0, 10)}</span>
              </div>
            ))}
          </Card>
        </Col>

        <Col span={12}>
          <Card title="最近回测" extra={<Button size="small" type="link" onClick={() => navigate("/backtest")}>全部 →</Button>}>
            {results.length === 0 ? (
              <Empty image={Empty.PRESENTED_IMAGE_SIMPLE} description="还没有回测结果" />
            ) : (
              <Table size="small" dataSource={results.slice(0, 6)} rowKey="id" pagination={false} showHeader={true}
                columns={[
                  { title: "股票", dataIndex: "ts_code", width: 85 },
                  { title: "收益", dataIndex: "total_return", width: 75, render: (v: number) => <span style={{ color: v > 0 ? "#52c41a" : "#ff4d4f" }}>{v}%</span> },
                  { title: "夏普", dataIndex: "sharpe_ratio", width: 65 },
                  { title: "回撤", dataIndex: "max_drawdown", width: 70, render: (v: number) => <span style={{ color: "#ff4d4f" }}>{v}%</span> },
                  { title: "时间", dataIndex: "created_at", width: 85, render: (v: string) => v?.slice(0, 10) },
                ]} />
            )}
          </Card>
        </Col>
      </Row>
    </div>
  );
}
