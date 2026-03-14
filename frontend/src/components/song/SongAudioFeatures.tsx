import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
} from "@/components/ui";
import type { AudioFeatures } from "@/types";

// Audio feature descriptions for tooltips
const FEATURE_DESCRIPTIONS: Record<string, string> = {
  bpm: "Beats per minute - the tempo of the track",
  energy: "Intensity and activity level of the track (0-100%)",
  danceability: "How suitable the track is for dancing (0-100%)",
  valence: "Musical positiveness - happy/cheerful vs sad/angry (0-100%)",
  speechiness: "Presence of spoken words in the track (0-100%)",
  acousticness: "Confidence the track is acoustic (0-100%)",
  instrumentalness: "Likelihood the track has no vocals (0-100%)",
  liveness: "Presence of a live audience (0-100%)",
  loudness: "Overall loudness in decibels (dB)",
  time_signature: "Beats per measure (e.g., 4/4, 3/4)",
};

// Color coding by intensity level
function getIntensityColor(value: number): string {
  if (value >= 80) return "bg-accent-peak";
  if (value >= 60) return "bg-accent-needle";
  if (value >= 40) return "bg-accent-warm";
  if (value >= 20) return "bg-accent-safe";
  return "bg-accent-cool";
}

function AudioFeatureBar({
  label,
  value,
  max = 100,
  displayValue,
  tooltip,
}: {
  label: string;
  value: number;
  max?: number;
  displayValue?: string;
  tooltip?: string;
}) {
  const percentage = Math.min((value / max) * 100, 100);
  const colorClass = getIntensityColor(percentage);

  return (
    <div className="space-y-1.5 group" title={tooltip}>
      <div className="flex items-center justify-between text-sm">
        <span className="text-zinc-400 flex items-center gap-1">
          {label}
          {tooltip && (
            <svg className="w-3.5 h-3.5 text-zinc-600 opacity-0 group-hover:opacity-100 transition-opacity" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
            </svg>
          )}
        </span>
        <span className="font-mono text-zinc-300">
          {displayValue || `${Math.round(percentage)}%`}
        </span>
      </div>
      <div className="h-2 bg-zinc-800 rounded-full overflow-hidden">
        <div
          className={`h-full rounded-full transition-all duration-500 ${colorClass}`}
          style={{ width: `${percentage}%` }}
        />
      </div>
    </div>
  );
}

interface SongAudioFeaturesProps {
  features: AudioFeatures;
  expanded: boolean;
  onToggleExpand: () => void;
}

export function SongAudioFeatures({ features, expanded, onToggleExpand }: SongAudioFeaturesProps) {
  // Primary features always shown
  const primaryFeatures = [
    { key: "bpm", label: "BPM", value: features.bpm, max: 200, displayFn: (v: number) => `${Math.round(v)}` },
    { key: "energy", label: "Energy", value: features.energy !== null ? features.energy * 100 : null, max: 100 },
    { key: "danceability", label: "Danceability", value: features.danceability !== null ? features.danceability * 100 : null, max: 100 },
    { key: "valence", label: "Valence", value: features.valence !== null ? features.valence * 100 : null, max: 100 },
  ];

  // Secondary features shown when expanded
  const secondaryFeatures = [
    { key: "speechiness", label: "Speechiness", value: features.speechiness !== null ? features.speechiness * 100 : null, max: 100 },
    { key: "acousticness", label: "Acousticness", value: features.acousticness !== null ? features.acousticness * 100 : null, max: 100 },
    { key: "instrumentalness", label: "Instrumentalness", value: features.instrumentalness !== null ? features.instrumentalness * 100 : null, max: 100 },
    { key: "liveness", label: "Liveness", value: features.liveness !== null ? features.liveness * 100 : null, max: 100 },
  ];

  // Technical audio features
  const technicalFeatures = [
    { key: "loudness", label: "Loudness", value: features.loudness, displayFn: (v: number) => `${v.toFixed(1)} dB` },
    { key: "time_signature", label: "Time Signature", value: features.time_signature, displayFn: (v: number) => `${v}/4` },
  ];

  const hasSecondaryFeatures = secondaryFeatures.some(f => f.value !== null);
  const hasTechnicalFeatures = technicalFeatures.some(f => f.value !== null);

  return (
    <Card variant="bordered">
      <CardHeader className="border-b border-zinc-800/50">
        <CardTitle className="text-base flex items-center gap-2">
          <svg className="w-4 h-4 text-accent-warm" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 19V6l12-3v13M9 19c0 1.105-1.343 2-3 2s-3-.895-3-2 1.343-2 3-2 3 .895 3 2zm12-3c0 1.105-1.343 2-3 2s-3-.895-3-2 1.343-2 3-2 3 .895 3 2zM9 10l12-3" />
          </svg>
          Audio Features
        </CardTitle>
      </CardHeader>
      <CardContent className="space-y-4">
        {/* Primary Features */}
        {primaryFeatures.map((feature) => (
          feature.value !== null && (
            <AudioFeatureBar
              key={feature.key}
              label={feature.label}
              value={feature.value}
              max={feature.max}
              displayValue={feature.displayFn ? feature.displayFn(feature.value) : undefined}
              tooltip={FEATURE_DESCRIPTIONS[feature.key]}
            />
          )
        ))}

        {/* Expandable Secondary Features */}
        {expanded && hasSecondaryFeatures && (
          <>
            <div className="border-t border-zinc-800/50 pt-4 mt-4">
              <p className="text-xs text-zinc-500 uppercase tracking-wide mb-3">Advanced Features</p>
            </div>
            {secondaryFeatures.map((feature) => (
              feature.value !== null && (
                <AudioFeatureBar
                  key={feature.key}
                  label={feature.label}
                  value={feature.value}
                  max={feature.max}
                  tooltip={FEATURE_DESCRIPTIONS[feature.key]}
                />
              )
            ))}
          </>
        )}

        {/* Technical Features */}
        {expanded && hasTechnicalFeatures && (
          <>
            <div className="border-t border-zinc-800/50 pt-4 mt-4">
              <p className="text-xs text-zinc-500 uppercase tracking-wide mb-3">Technical Details</p>
            </div>
            <div className="grid grid-cols-2 gap-4">
              {technicalFeatures.map((feature) => (
                feature.value !== null && (
                  <div key={feature.key} className="text-center p-3 bg-bg-panel rounded-lg" title={FEATURE_DESCRIPTIONS[feature.key]}>
                    <p className="text-lg font-bold text-zinc-200 font-mono">
                      {feature.displayFn ? feature.displayFn(feature.value) : feature.value}
                    </p>
                    <p className="text-xs text-zinc-500 mt-0.5">{feature.label}</p>
                  </div>
                )
              ))}
            </div>
          </>
        )}

        {/* Toggle Expand Button */}
        {(hasSecondaryFeatures || hasTechnicalFeatures) && (
          <button
            onClick={onToggleExpand}
            className="w-full mt-2 py-2 text-sm text-zinc-500 hover:text-zinc-300 transition-colors flex items-center justify-center gap-1"
          >
            {expanded ? "Show Less" : "Show All Features"}
            <svg
              className={`w-4 h-4 transition-transform ${expanded ? "rotate-180" : ""}`}
              fill="none"
              viewBox="0 0 24 24"
              stroke="currentColor"
            >
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
            </svg>
          </button>
        )}
      </CardContent>
    </Card>
  );
}
