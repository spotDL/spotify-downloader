import { useState } from "react";
import { useSettingsStore } from "@/stores/settings";
import {
  Card,
  CardContent,
  CardHeader,
  Input,
  ToggleSwitch,
} from "@/components/ui";
import { SectionHeader } from "./SectionHeader";
import { useSettingsContext } from "./SettingsContext";

export function CredentialSettings() {
  const {
    spotifyClientId,
    spotifyClientSecret,
    spotifyUserAuth,
  } = useSettingsStore();

  const { changeSetting, changeInput } = useSettingsContext();
  const [showSecrets, setShowSecrets] = useState(false);

  return (
    <Card variant="bordered" className="animate-slide-up stagger-3">
      <CardHeader>
        <SectionHeader
          icon={
            <svg className="w-5 h-5" viewBox="0 0 24 24" fill="currentColor">
              <path d="M12 0C5.4 0 0 5.4 0 12s5.4 12 12 12 12-5.4 12-12S18.66 0 12 0zm5.521 17.34c-.24.359-.66.48-1.021.24-2.82-1.74-6.36-2.101-10.561-1.141-.418.122-.779-.179-.899-.539-.12-.421.18-.78.54-.9 4.56-1.021 8.52-.6 11.64 1.32.42.18.479.659.301 1.02zm1.44-3.3c-.301.42-.841.6-1.262.3-3.239-1.98-8.159-2.58-11.939-1.38-.479.12-1.02-.12-1.14-.6-.12-.48.12-1.021.6-1.141C9.6 9.9 15 10.561 18.72 12.84c.361.181.54.78.241 1.2zm.12-3.36C15.24 8.4 8.82 8.16 5.16 9.301c-.6.179-1.2-.181-1.38-.721-.18-.601.18-1.2.72-1.381 4.26-1.26 11.28-1.02 15.721 1.621.539.3.719 1.02.419 1.56-.299.421-1.02.599-1.559.3z" />
            </svg>
          }
          iconBg="bg-gradient-to-br from-[#1db954]/20 to-[#169c46]/20"
          iconColor="text-[#1db954]"
          title="Spotify Credentials"
          description="Optional API credentials for better rate limits"
        />
      </CardHeader>
      <CardContent className="space-y-5">
        <div className="p-3 rounded-lg bg-[var(--accent-warm)]/10 border border-[var(--accent-warm)]/20">
          <p className="text-sm text-[var(--accent-warm)]">
            Get your credentials from the{" "}
            <a
              href="https://developer.spotify.com/dashboard"
              target="_blank"
              rel="noopener noreferrer"
              className="underline hover:text-[var(--accent-warm)]/80"
            >
              Spotify Developer Dashboard
            </a>
          </p>
        </div>

        <Input
          label="Client ID"
          value={spotifyClientId}
          onChange={changeInput("spotifyClientId", "Client ID")}
          placeholder="Your Spotify Client ID"
        />

        <div className="relative">
          <Input
            label="Client Secret"
            type={showSecrets ? "text" : "password"}
            value={spotifyClientSecret}
            onChange={changeInput("spotifyClientSecret", "Client Secret")}
            placeholder="Your Spotify Client Secret"
          />
          <button
            type="button"
            onClick={() => setShowSecrets(!showSecrets)}
            className="absolute right-3 top-8 text-[var(--color-text-muted)] hover:text-[var(--color-text-primary)] transition-colors"
          >
            {showSecrets ? (
              <svg
                className="w-5 h-5"
                fill="none"
                viewBox="0 0 24 24"
                stroke="currentColor"
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={2}
                  d="M13.875 18.825A10.05 10.05 0 0112 19c-4.478 0-8.268-2.943-9.543-7a9.97 9.97 0 011.563-3.029m5.858.908a3 3 0 114.243 4.243M9.878 9.878l4.242 4.242M9.88 9.88l-3.29-3.29m7.532 7.532l3.29 3.29M3 3l3.59 3.59m0 0A9.953 9.953 0 0112 5c4.478 0 8.268 2.943 9.543 7a10.025 10.025 0 01-4.132 5.411m0 0L21 21"
                />
              </svg>
            ) : (
              <svg
                className="w-5 h-5"
                fill="none"
                viewBox="0 0 24 24"
                stroke="currentColor"
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={2}
                  d="M15 12a3 3 0 11-6 0 3 3 0 016 0z"
                />
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={2}
                  d="M2.458 12C3.732 7.943 7.523 5 12 5c4.478 0 8.268 2.943 9.542 7-1.274 4.057-5.064 7-9.542 7-4.477 0-8.268-2.943-9.542-7z"
                />
              </svg>
            )}
          </button>
        </div>

        <ToggleSwitch
          checked={spotifyUserAuth}
          onChange={(val) => changeSetting("spotifyUserAuth", val, "Spotify OAuth")}
          label="Use Spotify OAuth"
          description="Enable user authentication for accessing private playlists"
        />
      </CardContent>
    </Card>
  );
}
