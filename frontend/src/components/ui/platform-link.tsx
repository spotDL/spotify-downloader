import { clsx } from "clsx";
import { twMerge } from "tailwind-merge";
import type { PlatformInfo } from "@/types";

// Platform configuration
interface PlatformConfig {
  name: string;
  icon: React.ReactNode;
  color: string;
  urlPattern?: RegExp;
}

// Platform icons as SVG components
const SpotifyIcon = () => (
  <svg className="w-4 h-4" viewBox="0 0 24 24" fill="currentColor">
    <path d="M12 0C5.4 0 0 5.4 0 12s5.4 12 12 12 12-5.4 12-12S18.66 0 12 0zm5.521 17.34c-.24.359-.66.48-1.021.24-2.82-1.74-6.36-2.101-10.561-1.141-.418.122-.779-.179-.899-.539-.12-.421.18-.78.54-.9 4.56-1.021 8.52-.6 11.64 1.32.42.18.479.659.301 1.02zm1.44-3.3c-.301.42-.841.6-1.262.3-3.239-1.98-8.159-2.58-11.939-1.38-.479.12-1.02-.12-1.14-.6-.12-.48.12-1.021.6-1.141C9.6 9.9 15 10.561 18.72 12.84c.361.181.54.78.241 1.2zm.12-3.36C15.24 8.4 8.82 8.16 5.16 9.301c-.6.179-1.2-.181-1.38-.721-.18-.601.18-1.2.72-1.381 4.26-1.26 11.28-1.02 15.721 1.621.539.3.719 1.02.419 1.56-.299.421-1.02.599-1.559.3z" />
  </svg>
);

const AppleMusicIcon = () => (
  <svg className="w-4 h-4" viewBox="0 0 24 24" fill="currentColor">
    <path d="M23.994 6.124a9.23 9.23 0 00-.24-2.19c-.317-1.31-1.062-2.31-2.18-3.043a5.022 5.022 0 00-1.877-.726 10.496 10.496 0 00-1.564-.15c-.04-.003-.083-.01-.124-.013H5.986c-.152.01-.303.017-.455.026-.747.043-1.49.123-2.193.4-1.336.53-2.3 1.452-2.865 2.78-.192.448-.292.925-.363 1.408-.056.392-.088.785-.1 1.18 0 .032-.007.062-.01.093v12.223c.01.14.017.283.027.424.05.815.154 1.624.497 2.373.65 1.42 1.738 2.353 3.234 2.802.42.127.856.187 1.293.228.555.053 1.11.06 1.667.06h11.03a12.5 12.5 0 001.57-.1c.822-.107 1.596-.342 2.296-.81a5.046 5.046 0 001.88-2.01c.186-.394.328-.81.406-1.233.138-.752.187-1.513.19-2.275 0-.21-.005-.42-.005-.63V6.124h-.01zm-6.92 8.45v3.858c0 .37-.006.742-.06 1.11-.043.29-.178.546-.47.684a1.07 1.07 0 01-.458.113c-.418.01-.837.003-1.255-.025-.328-.022-.65-.094-.944-.255-.41-.22-.706-.538-.877-.964a2.53 2.53 0 01-.14-.544 4.33 4.33 0 01-.032-.685c.01-.452.203-.832.513-1.142.322-.32.718-.51 1.148-.612.31-.072.626-.11.942-.14.29-.027.58-.044.87-.07l.02-.002V9.05c0-.205-.035-.4-.218-.535a.664.664 0 00-.26-.1 3.13 3.13 0 00-.424-.038l-3.822.37c-.32.032-.64.068-.96.1l-.04.005v7.59c0 .422.01.843-.04 1.263-.033.285-.145.544-.393.72-.157.112-.34.17-.534.196a6.04 6.04 0 01-1.163.01c-.347-.024-.686-.092-.996-.268-.392-.223-.682-.536-.845-.95a2.24 2.24 0 01-.148-.64 3.85 3.85 0 01.042-.908c.086-.453.315-.833.68-1.12.33-.26.713-.412 1.117-.496a7.9 7.9 0 011.18-.153c.217-.01.435-.025.65-.053l.025-.002V6.755c0-.11.003-.218.012-.327.03-.363.195-.673.53-.876a1.35 1.35 0 01.503-.172c.23-.034.46-.048.69-.058l1.2-.032c.324-.006.646 0 .97.006l1.11.038c.45.016.9.04 1.35.08.347.03.687.1.993.265.36.195.592.48.696.878.054.21.075.423.075.64l-.002 7.393z" />
  </svg>
);

const DeezerIcon = () => (
  <svg className="w-4 h-4" viewBox="0 0 24 24" fill="currentColor">
    <path d="M18.81 4.16v3.03H24V4.16h-5.19zM6.27 8.38v3.027h5.189V8.38h-5.19zm12.54 0v3.027H24V8.38h-5.19zM6.27 12.594v3.027h5.189v-3.027h-5.19zm6.27 0v3.027h5.19v-3.027h-5.19zm6.27 0v3.027H24v-3.027h-5.19zm-18.81 0v3.027h5.19v-3.027H0zm6.27 4.213v3.028h5.189v-3.028h-5.19zm6.27 0v3.028h5.19v-3.028h-5.19zm6.27 0v3.028H24v-3.028h-5.19zm-18.81 0v3.028h5.19v-3.028H0z" />
  </svg>
);

const YouTubeIcon = () => (
  <svg className="w-4 h-4" viewBox="0 0 24 24" fill="currentColor">
    <path d="M23.498 6.186a3.016 3.016 0 00-2.122-2.136C19.505 3.545 12 3.545 12 3.545s-7.505 0-9.377.505A3.017 3.017 0 00.502 6.186C0 8.07 0 12 0 12s0 3.93.502 5.814a3.016 3.016 0 002.122 2.136c1.871.505 9.376.505 9.376.505s7.505 0 9.377-.505a3.015 3.015 0 002.122-2.136C24 15.93 24 12 24 12s0-3.93-.502-5.814zM9.545 15.568V8.432L15.818 12l-6.273 3.568z" />
  </svg>
);

const SoundCloudIcon = () => (
  <svg className="w-4 h-4" viewBox="0 0 24 24" fill="currentColor">
    <path d="M1.175 12.225c-.051 0-.094.046-.101.1l-.233 2.154.233 2.105c.007.058.05.098.101.098.05 0 .09-.04.099-.098l.255-2.105-.27-2.154c-.009-.06-.052-.1-.084-.1zm-.899 1.025c-.051 0-.09.037-.097.094l-.156 1.135.156 1.105c.007.057.046.094.097.094.05 0 .087-.037.097-.094l.178-1.105-.178-1.135c-.01-.057-.047-.094-.097-.094zm1.979-.764c-.057 0-.103.047-.11.11l-.21 1.893.21 1.824c.007.064.053.11.11.11.058 0 .102-.046.11-.11l.234-1.824-.234-1.893c-.008-.063-.052-.11-.11-.11zm.943-.224c-.063 0-.114.051-.121.117l-.187 2.07.187 1.988c.007.07.058.121.121.121.064 0 .115-.051.121-.121l.21-1.988-.21-2.07c-.006-.066-.057-.117-.121-.117zm.964-.135c-.07 0-.124.057-.131.127l-.164 2.205.164 2.05c.007.076.061.133.131.133s.124-.057.131-.133l.186-2.05-.186-2.205c-.007-.07-.061-.127-.131-.127zm.982-.093c-.076 0-.135.06-.143.14l-.14 2.298.14 2.098c.008.082.067.142.143.142.077 0 .136-.06.143-.142l.159-2.098-.159-2.298c-.007-.08-.066-.14-.143-.14zm1.016-.085c-.082 0-.148.066-.154.15l-.117 2.39.117 2.126c.006.088.072.156.154.156.083 0 .149-.068.155-.156l.133-2.126-.133-2.39c-.006-.084-.072-.15-.155-.15zm.981-.074c-.089 0-.159.07-.165.16l-.093 2.459.093 2.148c.006.095.076.164.165.164.09 0 .16-.07.166-.164l.106-2.148-.106-2.459c-.006-.09-.076-.16-.166-.16zm1.001-.073c-.095 0-.168.076-.175.171l-.07 2.532.07 2.162c.007.1.08.178.175.178.096 0 .17-.078.176-.178l.08-2.162-.08-2.532c-.006-.095-.08-.171-.176-.171zm.998-.065c-.1 0-.178.08-.184.183l-.047 2.597.047 2.174c.006.107.084.19.184.19.102 0 .18-.083.186-.19l.054-2.174-.054-2.597c-.006-.103-.084-.183-.186-.183zm1.004-.06c-.107 0-.19.085-.196.194l-.023 2.657.023 2.186c.006.113.089.2.196.2.108 0 .191-.087.197-.2l.027-2.186-.027-2.657c-.006-.11-.089-.194-.197-.194zm1.07-.01c-.113 0-.2.088-.206.2v.01l-.01 2.66.01 2.196c.006.118.093.21.206.21.115 0 .203-.092.208-.21l.012-2.196-.012-2.67c-.005-.112-.093-.2-.208-.2zm1.082.063c-.119 0-.211.095-.216.215l.002 2.6.007 2.195c.005.124.097.22.207.22.112 0 .204-.096.209-.22l.002-2.195-.002-2.6c-.005-.12-.097-.215-.21-.215zm.906-.05c-.119 0-.213.1-.217.22l-.003 2.646.003 2.196c.004.127.098.224.217.224.12 0 .214-.097.217-.224l.003-2.196-.003-2.646c-.003-.12-.097-.22-.217-.22zm.969-.01c-.125 0-.222.1-.226.226v.007l-.003 2.64.003 2.195c.004.133.101.233.226.233.127 0 .224-.1.227-.233l.003-2.195-.003-2.647c-.003-.126-.1-.226-.227-.226zm1.083 5.327c-.127 0-.225-.101-.228-.228l-.002-2.2.002-2.643c.003-.127.101-.228.228-.228.128 0 .226.101.228.228l.003 2.643-.003 2.2c-.002.127-.1.228-.228.228z" />
  </svg>
);

const BandcampIcon = () => (
  <svg className="w-4 h-4" viewBox="0 0 24 24" fill="currentColor">
    <path d="M0 18.75l7.437-13.5H24l-7.438 13.5H0z" />
  </svg>
);

const TidalIcon = () => (
  <svg className="w-4 h-4" viewBox="0 0 24 24" fill="currentColor">
    <path d="M12.012 3.992L8.008 7.996 4.004 3.992 0 7.996l4.004 4.004L8.008 8l4.004 4.004L12.012 8l4.004 4.004L20.02 7.996l-4.004-4.004-4.004 4.004zM12.012 12.004l-4.004 4.004L12.012 20l4.004-4.004-4.004-4.004z" />
  </svg>
);

const DefaultIcon = () => (
  <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13.828 10.172a4 4 0 00-5.656 0l-4 4a4 4 0 105.656 5.656l1.102-1.101m-.758-4.899a4 4 0 005.656 0l4-4a4 4 0 00-5.656-5.656l-1.1 1.1" />
  </svg>
);

const platformConfigs: Record<string, PlatformConfig> = {
  spotify: {
    name: "Spotify",
    icon: <SpotifyIcon />,
    color: "#1db954",
    urlPattern: /open\.spotify\.com/,
  },
  apple_music: {
    name: "Apple Music",
    icon: <AppleMusicIcon />,
    color: "#fc3c44",
    urlPattern: /music\.apple\.com/,
  },
  deezer: {
    name: "Deezer",
    icon: <DeezerIcon />,
    color: "#a238ff",
    urlPattern: /deezer\.com/,
  },
  youtube: {
    name: "YouTube",
    icon: <YouTubeIcon />,
    color: "#ff0000",
    urlPattern: /youtube\.com|youtu\.be/,
  },
  youtube_music: {
    name: "YouTube Music",
    icon: <YouTubeIcon />,
    color: "#ff0000",
    urlPattern: /music\.youtube\.com/,
  },
  soundcloud: {
    name: "SoundCloud",
    icon: <SoundCloudIcon />,
    color: "#ff5500",
    urlPattern: /soundcloud\.com/,
  },
  bandcamp: {
    name: "Bandcamp",
    icon: <BandcampIcon />,
    color: "#1da0c3",
    urlPattern: /bandcamp\.com/,
  },
  tidal: {
    name: "TIDAL",
    icon: <TidalIcon />,
    color: "#000000",
    urlPattern: /tidal\.com/,
  },
};

export interface PlatformLinkProps {
  /** Platform info */
  platform: PlatformInfo;
  /** Size variant */
  size?: "sm" | "md" | "lg";
  /** Show followers count */
  showFollowers?: boolean;
  /** Additional class names */
  className?: string;
}

export function PlatformLink({
  platform,
  size = "md",
  showFollowers = false,
  className,
}: PlatformLinkProps) {
  const config = platformConfigs[platform.platform] ?? {
    name: platform.platform,
    icon: <DefaultIcon />,
    color: "var(--color-text-muted)",
  };

  const sizeClasses = {
    sm: "px-2 py-1 text-xs gap-1.5",
    md: "px-3 py-2 text-sm gap-2",
    lg: "px-4 py-2.5 text-base gap-2.5",
  };

  // Validate URL
  const isValidUrl = (url: string): boolean => {
    try {
      new URL(url);
      return true;
    } catch {
      return false;
    }
  };

  if (!isValidUrl(platform.url)) {
    return null;
  }

  return (
    <a
      href={platform.url}
      target="_blank"
      rel="noopener noreferrer"
      className={twMerge(
        clsx(
          "platform-link inline-flex items-center font-medium",
          "bg-[var(--bg-surface)] border border-[var(--color-border-subtle)]",
          "rounded-xl text-[var(--color-text-primary)]",
          "transition-all duration-200",
          "hover:border-[var(--color-border)] hover:-translate-y-0.5",
          sizeClasses[size]
        ),
        className
      )}
      style={{
        "--platform-color": config.color,
      } as React.CSSProperties}
    >
      <span style={{ color: config.color }}>{config.icon}</span>
      <span>{config.name}</span>
      {showFollowers && platform.followers && (
        <span className="text-[var(--color-text-muted)] text-xs">
          {formatNumber(platform.followers)}
        </span>
      )}
    </a>
  );
}

/**
 * Grid of platform links
 */
export interface PlatformLinksGridProps {
  platforms: PlatformInfo[];
  size?: "sm" | "md" | "lg";
  showFollowers?: boolean;
  className?: string;
}

export function PlatformLinksGrid({
  platforms,
  size = "md",
  showFollowers = false,
  className,
}: PlatformLinksGridProps) {
  // Filter out invalid platforms and deduplicate
  const validPlatforms = platforms.filter((p) => {
    try {
      new URL(p.url);
      return true;
    } catch {
      return false;
    }
  });

  if (validPlatforms.length === 0) {
    return null;
  }

  return (
    <div className={twMerge("flex flex-wrap gap-2", className)}>
      {validPlatforms.map((platform, index) => (
        <PlatformLink
          key={`${platform.platform}-${index}`}
          platform={platform}
          size={size}
          showFollowers={showFollowers}
        />
      ))}
    </div>
  );
}

// Helper function to format large numbers
function formatNumber(num: number): string {
  if (num >= 1000000) {
    return `${(num / 1000000).toFixed(1)}M`;
  }
  if (num >= 1000) {
    return `${(num / 1000).toFixed(1)}K`;
  }
  return num.toString();
}

export default PlatformLink;
