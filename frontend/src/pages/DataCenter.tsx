import { useState } from "react";
import { Card, Input, Table, Button, message, Space, Empty, Tag } from "antd";
import { SearchOutlined, SyncOutlined, DownloadOutlined } from "@ant-design/icons";
import * as api from "../api/client";

export default function DataCenter() {
  const [query, setQuery] = useState("");
  const [symbols, setSymbols] = useState<any[]>([]);
  const [searching, setSearching] = useState(false);
  const [syncing, setSyncing] = useState(false);

  const handleSearch = async () => {
    if (!query.trim()) return message.warning("请输入股票代码或名称");
    setSearching(true);
    try { setSymbols(await api.searchSymbols(query)); }
    catch { message.error("搜索失败"); }
    finally { setSearching(false); }
  };

  const handleSyncStocks = async () => {
    setSyncing(true);
    try {
      const res = await fetch("/api/data/sync/stocks", { method: "POST" });
      const data = await res.json();
      message.success(`已同步 ${data.synced} 只股票`);
    } catch { message.error("同步失败"); }
    finally { setSyncing(false); }
  };

  const handleSyncDaily = async (symbol: string) => {
    setSyncing(true);
    try {
      const res = await fetch("/api/data/sync/daily", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ symbols: [symbol], days_back: 730 }),
      });
      const data = await res.json();
      message.success(`已同步 ${data.synced} 条日K`);
    } catch { message.error("同步失败"); }
    finally { setSyncing(false); }
  };

  return (
    <div>
      <Card title="数据中心" extra={
        <Button icon={<SyncOutlined />} onClick={handleSyncStocks} loading={syncing}>同步股票列表</Button>
      }>
        <Space style={{ marginBottom: 16 }}>
          <Input.Search placeholder="搜索股票 (代码或名称)" value={query}
            onChange={e => setQuery(e.target.value)} onSearch={handleSearch}
            style={{ width: 300 }} enterButton={<SearchOutlined />} loading={searching} allowClear />
        </Space>

        <Table dataSource={symbols} rowKey="ts_code" loading={searching} size="middle"
          locale={{ emptyText: <Empty image={Empty.PRESENTED_IMAGE_SIMPLE} description={query ? "未找到匹配股票" : "输入代码或名称搜索"} /> }}
          columns={[
            { title: "代码", dataIndex: "ts_code", width: 110 },
            { title: "名称", dataIndex: "name", width: 130 },
            { title: "市场", dataIndex: "market", width: 60, render: (v: string) => <Tag>{v}</Tag> },
            { title: "操作", width: 100, render: (_: any, r: any) => (
              <Button size="small" icon={<DownloadOutlined />} onClick={() => handleSyncDaily(r.ts_code)} loading={syncing}>拉取数据</Button>
            )},
          ]}
          pagination={{ pageSize: 20, showSizeChanger: false }} />
      </Card>
    </div>
  );
}
