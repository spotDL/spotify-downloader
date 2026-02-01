import { createContext, useContext, useState, useEffect, useMemo, type ReactNode } from "react";
import { config, type DeploymentMode } from "@/config";

const DEV_MODE_OVERRIDE_KEY = "spotdl_dev_mode_override";

interface AppConfig {
  mode: DeploymentMode;
  downloadsEnabled: boolean;
  queueEnabled: boolean;
  downloadSettingsEnabled: boolean;
  apiUrl: string;
  version: string;
  githubUrl: string;
  isDev: boolean;
}

interface Features {
  canDownload: boolean;
  hasQueue: boolean;
  hasDownloadSettings: boolean;
  isHosted: boolean;
  isSelfHosted: boolean;
}

interface DevConfigContextType {
  /** Current effective config (with override applied if active) */
  config: AppConfig;
  /** Current effective features (with override applied if active) */
  features: Features;
  /** Base config from environment (without override) */
  baseConfig: AppConfig;
  /** Base features from environment (without override) */
  baseFeatures: Features;
  /** Current mode override (null if using env default) */
  modeOverride: DeploymentMode | null;
  /** Set mode override (null to clear) */
  setModeOverride: (mode: DeploymentMode | null) => void;
  /** Whether config is currently overridden */
  isOverridden: boolean;
}

const DevConfigContext = createContext<DevConfigContextType | null>(null);

function computeConfig(mode: DeploymentMode): AppConfig {
  const isHosted = mode === "hosted";
  return {
    mode,
    downloadsEnabled: !isHosted,
    queueEnabled: !isHosted,
    downloadSettingsEnabled: !isHosted,
    apiUrl: config.apiUrl,
    version: config.version,
    githubUrl: config.githubUrl,
    isDev: config.isDev,
  };
}

function computeFeatures(cfg: AppConfig): Features {
  return {
    canDownload: cfg.downloadsEnabled,
    hasQueue: cfg.queueEnabled,
    hasDownloadSettings: cfg.downloadSettingsEnabled,
    isHosted: cfg.mode === "hosted",
    isSelfHosted: cfg.mode === "self-hosted",
  };
}

interface DevConfigProviderProps {
  children: ReactNode;
}

export function DevConfigProvider({ children }: DevConfigProviderProps) {
  // Load initial override from localStorage (only in dev mode)
  const [modeOverride, setModeOverrideState] = useState<DeploymentMode | null>(() => {
    if (!config.isDev) return null;
    try {
      const stored = localStorage.getItem(DEV_MODE_OVERRIDE_KEY);
      if (stored === "hosted" || stored === "self-hosted") {
        return stored;
      }
    } catch {
      // Ignore localStorage errors
    }
    return null;
  });

  // Persist override to localStorage
  useEffect(() => {
    if (!config.isDev) return;
    try {
      if (modeOverride) {
        localStorage.setItem(DEV_MODE_OVERRIDE_KEY, modeOverride);
      } else {
        localStorage.removeItem(DEV_MODE_OVERRIDE_KEY);
      }
    } catch {
      // Ignore localStorage errors
    }
  }, [modeOverride]);

  // Compute base config/features (from env)
  const baseConfig = useMemo(() => computeConfig(config.mode), []);
  const baseFeatures = useMemo(() => computeFeatures(baseConfig), [baseConfig]);

  // Compute effective config/features (with override if in dev mode)
  const effectiveConfig = useMemo(() => {
    if (!config.isDev || !modeOverride) {
      return baseConfig;
    }
    return computeConfig(modeOverride);
  }, [baseConfig, modeOverride]);

  const effectiveFeatures = useMemo(
    () => computeFeatures(effectiveConfig),
    [effectiveConfig]
  );

  const setModeOverride = (mode: DeploymentMode | null) => {
    if (!config.isDev) return;
    setModeOverrideState(mode);
  };

  const value: DevConfigContextType = {
    config: effectiveConfig,
    features: effectiveFeatures,
    baseConfig,
    baseFeatures,
    modeOverride,
    setModeOverride,
    isOverridden: config.isDev && modeOverride !== null,
  };

  return (
    <DevConfigContext.Provider value={value}>
      {children}
    </DevConfigContext.Provider>
  );
}

export function useDevConfig(): DevConfigContextType {
  const context = useContext(DevConfigContext);
  if (!context) {
    throw new Error("useDevConfig must be used within a DevConfigProvider");
  }
  return context;
}

/**
 * Convenience hook that returns just features.
 * Use this in components that only need feature flags.
 */
export function useFeatures(): Features {
  const { features } = useDevConfig();
  return features;
}
