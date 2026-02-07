/**
 * Application configuration based on environment variables.
 *
 * Two deployment modes:
 * - Hosted: Public instance - crowdsourced match database, search/matches/API
 *           This is the central matching service that self-hosted instances can use
 * - Self-hosted: Full functionality including downloads, can use hosted matching API
 *
 * Set VITE_DEPLOYMENT_MODE=hosted for the public instance
 * Self-hosted is the default mode
 */

export type DeploymentMode = "hosted" | "self-hosted";

interface AppConfig {
  /** Deployment mode: 'hosted' or 'self-hosted' */
  mode: DeploymentMode;

  /** Whether downloads are enabled (false for hosted mode) */
  downloadsEnabled: boolean;

  /** Whether the queue page should be shown */
  queueEnabled: boolean;

  /** Whether download settings should be shown */
  downloadSettingsEnabled: boolean;

  /** API base URL */
  apiUrl: string;

  /** Application version */
  version: string;

  /** GitHub repository URL */
  githubUrl: string;

  /** Whether this is a development build */
  isDev: boolean;
}

const deploymentMode = (import.meta.env.VITE_DEPLOYMENT_MODE as DeploymentMode) || "self-hosted";
const isHosted = deploymentMode === "hosted";

export const config: AppConfig = {
  mode: deploymentMode,

  // Hosted mode: Crowdsourced matching service (no downloads)
  // Self-hosted mode: Full download functionality
  downloadsEnabled: !isHosted,
  queueEnabled: !isHosted,
  downloadSettingsEnabled: !isHosted,

  // API configuration
  apiUrl: import.meta.env.VITE_API_URL || "",

  // Application info
  version: import.meta.env.VITE_APP_VERSION || "5.0.0",
  githubUrl: "https://github.com/spotDL/spotify-downloader",

  // Development mode
  isDev: import.meta.env.DEV,
};

/**
 * React hook to access configuration
 */
export function useConfig() {
  return config;
}

/**
 * Feature flags based on configuration
 */
export const features = {
  /** Can users download songs? */
  canDownload: config.downloadsEnabled,

  /** Is the queue page available? */
  hasQueue: config.queueEnabled,

  /** Are download settings shown? */
  hasDownloadSettings: config.downloadSettingsEnabled,

  /** Is this the hosted public instance? */
  isHosted: config.mode === "hosted",

  /** Is this a self-hosted instance? */
  isSelfHosted: config.mode === "self-hosted",
} as const;
