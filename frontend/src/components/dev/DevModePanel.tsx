import { useState, useEffect, useRef } from "react";
import { clsx } from "clsx";
import { useDevConfig } from "@/contexts/DevConfigContext";
import type { DeploymentMode } from "@/config";

const POSITION_KEY = "spotdl_dev_panel_position";

interface Position {
  x: number;
  y: number;
}

function getStoredPosition(): Position {
  try {
    const stored = localStorage.getItem(POSITION_KEY);
    if (stored) {
      const pos = JSON.parse(stored);
      if (typeof pos.x === "number" && typeof pos.y === "number") {
        return pos;
      }
    }
  } catch {
    // Ignore
  }
  return { x: 20, y: 20 };
}

function storePosition(pos: Position) {
  try {
    localStorage.setItem(POSITION_KEY, JSON.stringify(pos));
  } catch {
    // Ignore
  }
}

export function DevModePanel() {
  const { baseConfig, modeOverride, setModeOverride, isOverridden, features } =
    useDevConfig();

  const [isExpanded, setIsExpanded] = useState(false);
  const [position, setPosition] = useState<Position>(getStoredPosition);
  const [isDragging, setIsDragging] = useState(false);
  const dragStartRef = useRef<{ x: number; y: number; posX: number; posY: number } | null>(null);
  const positionRef = useRef<Position>(position);
  const panelRef = useRef<HTMLDivElement>(null);

  // Keep ref in sync with state
  useEffect(() => {
    positionRef.current = position;
  }, [position]);

  // Don't render in production
  if (!baseConfig.isDev) {
    return null;
  }

  const currentMode: DeploymentMode = modeOverride ?? baseConfig.mode;

  const handleMouseDown = (e: React.MouseEvent) => {
    if ((e.target as HTMLElement).closest("button")) return;
    setIsDragging(true);
    dragStartRef.current = {
      x: e.clientX,
      y: e.clientY,
      posX: position.x,
      posY: position.y,
    };
  };

  useEffect(() => {
    if (!isDragging) return;

    const handleMouseMove = (e: MouseEvent) => {
      if (!dragStartRef.current) return;
      const dx = e.clientX - dragStartRef.current.x;
      const dy = e.clientY - dragStartRef.current.y;
      const newPos = {
        x: Math.max(0, Math.min(window.innerWidth - 200, dragStartRef.current.posX + dx)),
        y: Math.max(0, Math.min(window.innerHeight - 100, dragStartRef.current.posY + dy)),
      };
      setPosition(newPos);
    };

    const handleMouseUp = () => {
      setIsDragging(false);
      storePosition(positionRef.current);
    };

    document.addEventListener("mousemove", handleMouseMove);
    document.addEventListener("mouseup", handleMouseUp);
    return () => {
      document.removeEventListener("mousemove", handleMouseMove);
      document.removeEventListener("mouseup", handleMouseUp);
    };
  }, [isDragging]);

  const modeOptions: { value: DeploymentMode | null; label: string; description: string }[] = [
    { value: null, label: "Env", description: `Use ${baseConfig.mode} from .env` },
    { value: "self-hosted", label: "Self", description: "Self-hosted mode" },
    { value: "hosted", label: "Hosted", description: "Hosted mode" },
  ];

  return (
    <div
      ref={panelRef}
      className={clsx(
        "fixed z-[9999] select-none",
        "transition-all duration-200",
        isDragging && "cursor-grabbing"
      )}
      style={{ left: position.x, top: position.y }}
    >
      {/* Collapsed state - pill */}
      {!isExpanded && (
        <button
          onMouseDown={handleMouseDown}
          onClick={() => !isDragging && setIsExpanded(true)}
          className={clsx(
            "flex items-center gap-2 px-3 py-1.5 rounded-full",
            "text-xs font-medium",
            "backdrop-blur-md",
            "cursor-grab active:cursor-grabbing",
            "transition-all duration-200",
            isOverridden
              ? "bg-amber-500/20 border border-amber-500/40 text-amber-300"
              : "bg-zinc-800/80 border border-zinc-700/50 text-zinc-400"
          )}
        >
          <span
            className={clsx(
              "w-2 h-2 rounded-full",
              currentMode === "self-hosted" ? "bg-green-500" : "bg-amber-500"
            )}
          />
          <span>DEV</span>
          {isOverridden && <span className="text-amber-400">*</span>}
        </button>
      )}

      {/* Expanded state - panel */}
      {isExpanded && (
        <div
          onMouseDown={handleMouseDown}
          className={clsx(
            "w-64 rounded-xl",
            "backdrop-blur-md",
            "transition-all duration-200",
            isOverridden
              ? "bg-zinc-900/95 border-2 border-amber-500/50"
              : "bg-zinc-900/95 border border-zinc-700/50"
          )}
        >
          {/* Header */}
          <div
            className={clsx(
              "flex items-center justify-between px-3 py-2",
              "border-b border-zinc-700/50",
              "cursor-grab active:cursor-grabbing"
            )}
          >
            <div className="flex items-center gap-2">
              <div
                className={clsx(
                  "w-2 h-2 rounded-full",
                  currentMode === "self-hosted" ? "bg-green-500" : "bg-amber-500"
                )}
              />
              <span className="text-xs font-semibold text-zinc-300">
                Dev Mode
              </span>
              {isOverridden && (
                <span className="px-1.5 py-0.5 text-[10px] font-medium rounded bg-amber-500/20 text-amber-400">
                  OVERRIDE
                </span>
              )}
            </div>
            <button
              onClick={() => setIsExpanded(false)}
              className="p-1 rounded hover:bg-zinc-700/50 text-zinc-500 hover:text-zinc-300 transition-colors"
            >
              <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
              </svg>
            </button>
          </div>

          {/* Content */}
          <div className="p-3 space-y-3">
            {/* Mode selector */}
            <div className="space-y-1.5">
              <label className="text-[10px] font-medium text-zinc-500 uppercase tracking-wider">
                Deployment Mode
              </label>
              <div className="flex gap-1">
                {modeOptions.map((opt) => {
                  const isActive =
                    (opt.value === null && !modeOverride) ||
                    (opt.value !== null && modeOverride === opt.value);
                  return (
                    <button
                      key={opt.label}
                      onClick={() => setModeOverride(opt.value)}
                      title={opt.description}
                      className={clsx(
                        "flex-1 px-2 py-1.5 rounded-lg text-xs font-medium",
                        "transition-all duration-150",
                        isActive
                          ? "bg-[var(--accent-safe)] text-white"
                          : "bg-zinc-800 text-zinc-400 hover:bg-zinc-700 hover:text-zinc-300"
                      )}
                    >
                      {opt.label}
                    </button>
                  );
                })}
              </div>
            </div>

            {/* Feature indicators */}
            <div className="space-y-1.5">
              <label className="text-[10px] font-medium text-zinc-500 uppercase tracking-wider">
                Active Features
              </label>
              <div className="grid grid-cols-2 gap-1.5 text-[10px]">
                <FeatureIndicator label="Downloads" enabled={features.canDownload} />
                <FeatureIndicator label="Queue" enabled={features.hasQueue} />
                <FeatureIndicator label="Settings" enabled={features.hasDownloadSettings} />
                <FeatureIndicator
                  label={features.isHosted ? "Hosted" : "Self-hosted"}
                  enabled={true}
                  variant={features.isHosted ? "amber" : "green"}
                />
              </div>
            </div>

            {/* Reset button */}
            {isOverridden && (
              <button
                onClick={() => setModeOverride(null)}
                className={clsx(
                  "w-full px-3 py-1.5 rounded-lg text-xs font-medium",
                  "bg-amber-500/20 text-amber-400 hover:bg-amber-500/30",
                  "transition-colors"
                )}
              >
                Reset to Environment
              </button>
            )}
          </div>

          {/* Footer */}
          <div className="px-3 py-2 border-t border-zinc-700/50">
            <p className="text-[10px] text-zinc-600">
              Env: {baseConfig.mode} • Effective: {currentMode}
            </p>
          </div>
        </div>
      )}
    </div>
  );
}

function FeatureIndicator({
  label,
  enabled,
  variant = "default",
}: {
  label: string;
  enabled: boolean;
  variant?: "default" | "green" | "amber";
}) {
  const colors = {
    default: enabled ? "bg-green-500/20 text-green-400" : "bg-zinc-700/50 text-zinc-500",
    green: "bg-green-500/20 text-green-400",
    amber: "bg-amber-500/20 text-amber-400",
  };

  return (
    <div
      className={clsx(
        "flex items-center gap-1.5 px-2 py-1 rounded",
        colors[variant]
      )}
    >
      <span
        className={clsx(
          "w-1.5 h-1.5 rounded-full",
          enabled
            ? variant === "amber"
              ? "bg-amber-500"
              : "bg-green-500"
            : "bg-zinc-500"
        )}
      />
      <span>{label}</span>
    </div>
  );
}

export default DevModePanel;
