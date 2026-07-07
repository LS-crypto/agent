import { defineConfig, loadEnv } from "vite";
import react from "@vitejs/plugin-react";
import { VitePWA } from "vite-plugin-pwa";

export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, process.cwd(), "");
  const isAndroid = env.VITE_PLATFORM === "android";

  return {
    plugins: [
      react(),
      VitePWA({
        disable: isAndroid,
        registerType: "autoUpdate",
          includeAssets: [
            "apple-touch-icon.png",
            "pwa-192x192.png",
            "pwa-512x512.png",
          ],
          manifest: {
            name: "烁士生",
            short_name: "烁士生",
            description: "烁士生 · AI 编程助手，连接云端 Agent",
            theme_color: "#1e1e1e",
            background_color: "#1e1e1e",
            display: "standalone",
            orientation: "any",
            scope: "/",
            start_url: "/",
            lang: "zh-CN",
            icons: [
              {
                src: "pwa-192x192.png",
                sizes: "192x192",
                type: "image/png",
              },
              {
                src: "pwa-512x512.png",
                sizes: "512x512",
                type: "image/png",
              },
              {
                src: "pwa-512x512.png",
                sizes: "512x512",
                type: "image/png",
                purpose: "maskable",
              },
            ],
          },
          workbox: {
            navigateFallback: "/index.html",
            navigateFallbackDenylist: [/^\/api/, /^\/health/],
            globPatterns: ["**/*.{js,css,html,ico,png,svg,woff,woff2}"],
            runtimeCaching: [],
          },
          devOptions: {
            enabled: false,
          },
        }),
    ],
    server: {
      port: 5173,
      proxy: {
        "/api": {
          target: "http://127.0.0.1:8765",
          changeOrigin: true,
        },
        "/health": {
          target: "http://127.0.0.1:8765",
          changeOrigin: true,
        },
      },
    },
  };
});
