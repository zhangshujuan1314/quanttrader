import React from "react";
import ReactDOM from "react-dom/client";
import { BrowserRouter } from "react-router-dom";
import { ConfigProvider, theme, App as AntApp, Result, Button } from "antd";
import zhCN from "antd/locale/zh_CN";
import App from "./App";

class RootErrorBoundary extends React.Component<{ children: React.ReactNode }, { error: Error | null }> {
  constructor(props: { children: React.ReactNode }) {
    super(props);
    this.state = { error: null };
  }
  static getDerivedStateFromError(error: Error) { return { error }; }
  render() {
    if (this.state.error) {
      return (
        <ConfigProvider locale={zhCN}>
          <Result status="error" title="页面加载失败" subTitle={this.state.error.message}
            extra={<Button type="primary" onClick={() => { this.setState({ error: null }); window.location.reload(); }}>重新加载</Button>} />
        </ConfigProvider>
      );
    }
    return this.props.children;
  }
}

ReactDOM.createRoot(document.getElementById("root")!).render(
  <React.StrictMode>
    <RootErrorBoundary>
      <ConfigProvider
        locale={zhCN}
        theme={{
          algorithm: theme.defaultAlgorithm,
          token: { colorPrimary: "#1677ff", borderRadius: 6 },
        }}
      >
        <BrowserRouter>
          <App />
        </BrowserRouter>
      </ConfigProvider>
    </RootErrorBoundary>
  </React.StrictMode>
);
