const INSTALL_DISMISS_KEY = "sheldon-pwa-install-dismissed";

export interface BeforeInstallPromptEvent extends Event {
  prompt: () => Promise<void>;
  userChoice: Promise<{ outcome: "accepted" | "dismissed" }>;
}

/** Capacitor 原生壳内不需要 PWA 安装条 */
export function isNativeApp(): boolean {
  try {
    const cap = (
      window as Window & {
        Capacitor?: { isNativePlatform?: () => boolean };
      }
    ).Capacitor;
    return cap?.isNativePlatform?.() === true;
  } catch {
    return import.meta.env.VITE_PLATFORM === "android";
  }
}

/** 已添加到主屏幕或以 standalone 打开 */
export function isStandalone(): boolean {
  return (
    window.matchMedia("(display-mode: standalone)").matches ||
    (window.navigator as Navigator & { standalone?: boolean }).standalone ===
      true
  );
}

export function isMobileDevice(): boolean {
  return (
    /Android|iPhone|iPad|iPod/i.test(navigator.userAgent) ||
    window.innerWidth <= 768
  );
}

export function isIos(): boolean {
  return /iPhone|iPad|iPod/i.test(navigator.userAgent);
}

export function isInstallBannerDismissed(): boolean {
  try {
    return localStorage.getItem(INSTALL_DISMISS_KEY) === "1";
  } catch {
    return false;
  }
}

export function dismissInstallBanner(): void {
  try {
    localStorage.setItem(INSTALL_DISMISS_KEY, "1");
  } catch {
    /* private mode */
  }
}
