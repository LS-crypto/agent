import type { CapacitorConfig } from "@capacitor/cli";

const config: CapacitorConfig = {
  appId: "com.sheldon.agent",
  appName: "烁士生",
  webDir: "dist",
  android: {
    allowMixedContent: true,
    backgroundColor: "#1e1e1e",
  },
  server: {
    // http 避免 https WebView 请求 http ECS API 被混合内容拦截
    androidScheme: "http",
  },
};

export default config;
