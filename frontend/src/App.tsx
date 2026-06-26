import { Routes, Route, useNavigate, useLocation } from "react-router-dom";
import { Layout, Menu } from "antd";
import {
  DashboardOutlined,
  CodeOutlined,
  LineChartOutlined,
  DatabaseOutlined,
  SwapOutlined,
} from "@ant-design/icons";
import Dashboard from "./pages/Dashboard";
import StrategyEditor from "./pages/StrategyEditor";
import BacktestView from "./pages/BacktestView";
import DataCenter from "./pages/DataCenter";
import TradePanel from "./pages/TradePanel";

const { Sider, Content } = Layout;

const menuItems = [
  { key: "/", icon: <DashboardOutlined />, label: "仪表盘" },
  { key: "/strategy", icon: <CodeOutlined />, label: "策略工坊" },
  { key: "/backtest", icon: <LineChartOutlined />, label: "回测中心" },
  { key: "/trade", icon: <SwapOutlined />, label: "模拟交易" },
  { key: "/data", icon: <DatabaseOutlined />, label: "数据中心" },
];

export default function App() {
  const navigate = useNavigate();
  const location = useLocation();

  return (
    <Layout style={{ minHeight: "100vh" }}>
      <Sider
        width={200}
        style={{ background: "#fff", borderRight: "1px solid #f0f0f0" }}
      >
        <div
          style={{
            height: 48, display: "flex", alignItems: "center",
            justifyContent: "center", fontWeight: 700, fontSize: 16,
            borderBottom: "1px solid #f0f0f0",
          }}
        >
          量化智投
        </div>
        <Menu
          mode="inline"
          selectedKeys={[location.pathname]}
          items={menuItems}
          onClick={({ key }) => navigate(key)}
          style={{ borderRight: 0 }}
        />
      </Sider>
      <Layout>
        <Content style={{ padding: 24, background: "#f5f5f5", minHeight: "100vh" }}>
          <Routes>
            <Route path="/" element={<Dashboard />} />
            <Route path="/strategy" element={<StrategyEditor />} />
            <Route path="/backtest" element={<BacktestView />} />
            <Route path="/trade" element={<TradePanel />} />
            <Route path="/data" element={<DataCenter />} />
          </Routes>
        </Content>
      </Layout>
    </Layout>
  );
}
