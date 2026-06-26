import { useState, useEffect, useCallback } from "react";
import { Card, Row, Col, Button, Input, InputNumber, Select, Table, Tag, message, Space, Empty } from "antd";
import { SendOutlined, ReloadOutlined, AlertOutlined } from "@ant-design/icons";
import * as api from "../api/client";

export default function TradePanel() {
  const [account, setAccount] = useState<any>(null);
  const [orders, setOrders] = useState<any[]>([]);
  const [symbol, setSymbol] = useState("000001.SZ");
  const [action, setAction] = useState<"buy" | "sell">("buy");
  const [quantity, setQuantity] = useState(100);
  const [limitPrice, setLimitPrice] = useState<number | null>(null);
  const [price, setPrice] = useState(10.0);
  const [loading, setLoading] = useState(false);
  const [riskStatus, setRiskStatus] = useState<any>(null);

  const refresh = useCallback(async () => {
    try {
      const [acc, ords, risk] = await Promise.all([
        api.getAccount(), fetch("/api/trade/orders").then(r => r.json()), api.getRiskStatus(),
      ]);
      setAccount(acc); setOrders(ords); setRiskStatus(risk);
    } catch { /* ignore */ }
  }, []);

  useEffect(() => { refresh(); }, [refresh]);

  const handleSubmit = async () => {
    setLoading(true);
    try {
      const res = await api.placeOrder({ symbol, action, quantity, limit_price: limitPrice });
      if (res.status === "filled") message.success(`${action === "buy" ? "买入" : "卖出"} ${symbol} ×${quantity} @ ${res.filled_price}`);
      else message.error(res.reason || "订单被拒绝");
      refresh();
    } catch { message.error("下单失败"); }
    finally { setLoading(false); }
  };

  const handleUpdatePrice = async () => {
    try {
      await fetch("/api/trade/price", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ symbol, price }) });
      message.success(`${symbol} → ¥${price}`); refresh();
    } catch { message.error("更新失败"); }
  };

  const handleResetRisk = async () => {
    await fetch("/api/trade/risk/reset", { method: "POST" });
    message.success("风控已重置"); refresh();
  };

  const positionList = account?.positions ? Object.entries(account.positions).map(([sym, p]: [string, any]) => ({ key: sym, symbol: sym, ...p })) : [];

  return (
    <div>
      <Row gutter={16}>
        <Col span={6}>
          <Card size="small" title="账户概览" extra={<Button size="small" icon={<ReloadOutlined />} onClick={refresh} />}>
            {account ? <>
              <StatLine label="总资产" value={"¥" + (account.total_value ?? 0).toLocaleString()} />
              <StatLine label="现金" value={"¥" + (account.cash ?? 0).toLocaleString()} />
              <StatLine label="总盈亏" value={(account.total_pnl_pct ?? 0).toFixed(2) + "%"} color={account.total_pnl >= 0 ? "#52c41a" : "#ff4d4f"} />
            </> : <Empty image={Empty.PRESENTED_IMAGE_SIMPLE} description="无数据" />}
          </Card>

          <Card size="small" title={<Space><AlertOutlined />风控状态</Space>} style={{ marginTop: 12 }}
            extra={riskStatus?.circuit_broken && <Button size="small" danger onClick={handleResetRisk}>重置</Button>}>
            {riskStatus ? <>
              <Tag color={riskStatus.circuit_broken ? "red" : "green"}>{riskStatus.circuit_broken ? "已熔断" : "正常"}</Tag>
              <div style={{ fontSize: 12, color: "#999", marginTop: 8, lineHeight: 1.8 }}>
                <div>最大仓位: {(riskStatus.rules?.max_position_pct ?? 0) * 100}%</div>
                <div>单票上限: {(riskStatus.rules?.single_stock_limit_pct ?? 0) * 100}%</div>
                <div>止损线: {(riskStatus.rules?.stop_loss_pct ?? 0) * 100}%</div>
              </div>
            </> : null}
          </Card>
        </Col>

        <Col span={9}>
          <Card size="small" title="下单">
            <Space direction="vertical" style={{ width: "100%" }} size="small">
              <Input addonBefore="代码" value={symbol} onChange={e => setSymbol(e.target.value)} />
              <Select value={action} onChange={setAction} style={{ width: "100%" }}
                options={[{ label: "买入", value: "buy" }, { label: "卖出", value: "sell" }]} />
              <InputNumber addonBefore="数量" value={quantity} onChange={v => setQuantity(v ?? 100)} style={{ width: "100%" }} min={100} step={100} />
              <InputNumber addonBefore="限价" value={limitPrice} onChange={v => setLimitPrice(v)} style={{ width: "100%" }} min={0} precision={3} placeholder="空=市价" />
              <Button type="primary" icon={<SendOutlined />} block loading={loading} onClick={handleSubmit} danger={action === "sell"}>
                {action === "buy" ? "买入" : "卖出"}
              </Button>
            </Space>
          </Card>

          <Card size="small" title="行情报价" style={{ marginTop: 12 }}>
            <Space>
              <InputNumber addonBefore="¥" value={price} onChange={v => setPrice(v ?? 0)} min={0} precision={3} style={{ width: 180 }} />
              <Button onClick={handleUpdatePrice}>更新</Button>
            </Space>
          </Card>
        </Col>

        <Col span={9}>
          <Card size="small" title={`持仓 (${positionList.length})`}>
            {positionList.length > 0 ? (
              <Table size="small" dataSource={positionList} pagination={false}
                columns={[
                  { title: "代码", dataIndex: "symbol", width: 75 },
                  { title: "数量", dataIndex: "quantity", width: 55 },
                  { title: "成本", dataIndex: "avg_cost", width: 70, render: (v: number) => v?.toFixed(3) },
                  { title: "市值", dataIndex: "market_value", width: 80, render: (v: number) => v?.toFixed(2) },
                  { title: "盈亏%", dataIndex: "unrealized_pnl_pct", width: 65,
                    render: (v: number) => <span style={{ color: (v >= 0 ? "#52c41a" : "#ff4d4f") }}>{v?.toFixed(1)}%</span> },
                ]} />
            ) : <Empty image={Empty.PRESENTED_IMAGE_SIMPLE} description="暂无持仓" />}
          </Card>

          <Card size="small" title={`委托 (${orders.length})`} style={{ marginTop: 12 }}>
            <Table size="small" dataSource={orders} rowKey="id" pagination={{ pageSize: 8, size: "small" }}
              locale={{ emptyText: <Empty image={Empty.PRESENTED_IMAGE_SIMPLE} description="无委托" /> }}
              columns={[
                { title: "股票", dataIndex: "symbol", width: 75 },
                { title: "方向", dataIndex: "action", width: 45, render: (v: string) => <Tag color={v === "buy" ? "green" : "red"}>{v === "buy" ? "买" : "卖"}</Tag> },
                { title: "量", dataIndex: "quantity", width: 45 },
                { title: "成交价", dataIndex: "filled_price", width: 70, render: (v: number) => v ? v.toFixed(3) : "-" },
                { title: "状态", dataIndex: "status", width: 65,
                  render: (v: string) => { const cm: Record<string, string> = { filled: "green", rejected: "red", cancelled: "orange", submitted: "blue" }; return <Tag color={cm[v] || "default"}>{v}</Tag>; }},
              ]} />
          </Card>
        </Col>
      </Row>
    </div>
  );
}

function StatLine({ label, value, color }: { label: string; value: string; color?: string }) {
  return (
    <div style={{ marginBottom: 10 }}>
      <div style={{ fontSize: 12, color: "#999" }}>{label}</div>
      <div style={{ fontSize: 18, fontWeight: 600, color: color || "#333", marginTop: 2 }}>{value}</div>
    </div>
  );
}
