import { useCallback, useEffect, useState } from "react";
import {
  dismissInstallBanner,
  isInstallBannerDismissed,
  isIos,
  isMobileDevice,
  isNativeApp,
  isStandalone,
  type BeforeInstallPromptEvent,
} from "../pwa";
import "./InstallPrompt.css";

export function InstallPrompt() {
  const [visible, setVisible] = useState(false);
  const [deferredPrompt, setDeferredPrompt] =
    useState<BeforeInstallPromptEvent | null>(null);

  useEffect(() => {
    if (
      isNativeApp() ||
      isStandalone() ||
      isInstallBannerDismissed() ||
      !isMobileDevice()
    ) {
      return;
    }
    setVisible(true);
  }, []);

  useEffect(() => {
    const onBeforeInstall = (event: Event) => {
      event.preventDefault();
      setDeferredPrompt(event as BeforeInstallPromptEvent);
      if (!isStandalone() && !isInstallBannerDismissed() && isMobileDevice()) {
        setVisible(true);
      }
    };
    window.addEventListener("beforeinstallprompt", onBeforeInstall);
    return () =>
      window.removeEventListener("beforeinstallprompt", onBeforeInstall);
  }, []);

  const handleDismiss = useCallback(() => {
    dismissInstallBanner();
    setVisible(false);
  }, []);

  const handleInstall = useCallback(async () => {
    if (!deferredPrompt) return;
    await deferredPrompt.prompt();
    await deferredPrompt.userChoice;
    setDeferredPrompt(null);
    setVisible(false);
  }, [deferredPrompt]);

  if (!visible) return null;

  const ios = isIos();

  return (
    <div className="pwa-install-banner" role="region" aria-label="安装到主屏幕">
      <div className="pwa-install-body">
        <p className="pwa-install-title">安装烁士生</p>
        {ios ? (
          <p className="pwa-install-hint">
            点 Safari 底栏 <strong>分享</strong> → <strong>添加到主屏幕</strong>
            ，像 App 一样全屏使用（后端连 ECS 云端）。
          </p>
        ) : deferredPrompt ? (
          <p className="pwa-install-hint">
            添加到主屏幕，全屏打开 · 数据与对话保存在云端服务器。
          </p>
        ) : (
          <p className="pwa-install-hint">
            浏览器菜单中选择 <strong>安装应用</strong> 或{" "}
            <strong>添加到主屏幕</strong>。
          </p>
        )}
        <div className="pwa-install-actions">
          {!ios && deferredPrompt && (
            <button
              type="button"
              className="pwa-install-btn primary"
              onClick={() => void handleInstall()}
            >
              安装
            </button>
          )}
          <button
            type="button"
            className="pwa-install-btn"
            onClick={handleDismiss}
          >
            暂不
          </button>
        </div>
      </div>
    </div>
  );
}
