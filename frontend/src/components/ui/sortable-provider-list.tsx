import {
  DndContext,
  closestCenter,
  KeyboardSensor,
  PointerSensor,
  useSensor,
  useSensors,
  type DragEndEvent,
} from "@dnd-kit/core";
import {
  arrayMove,
  SortableContext,
  sortableKeyboardCoordinates,
  useSortable,
  verticalListSortingStrategy,
} from "@dnd-kit/sortable";
import { CSS } from "@dnd-kit/utilities";
import { clsx } from "clsx";
import { ToggleSwitch } from "./toggle-switch";

export interface ProviderPreference {
  id: string;
  enabled: boolean;
}

export interface ProviderInfo {
  id: string;
  name: string;
  icon: string;
  default_enabled: boolean;
}

interface SortableProviderItemProps {
  preference: ProviderPreference;
  provider: ProviderInfo;
  index: number;
  onToggle: (id: string) => void;
}

function SortableProviderItem({
  preference,
  provider,
  index,
  onToggle,
}: SortableProviderItemProps) {
  const {
    attributes,
    listeners,
    setNodeRef,
    transform,
    transition,
    isDragging,
  } = useSortable({ id: preference.id });

  const style = {
    transform: CSS.Transform.toString(transform),
    transition,
  };

  return (
    <div
      ref={setNodeRef}
      style={style}
      className={clsx(
        "flex items-center gap-3 px-3 py-2.5 rounded-lg",
        "bg-[var(--bg-surface)] border border-[var(--color-border-subtle)]",
        "transition-colors",
        isDragging && "opacity-50 border-[var(--accent-needle)]",
        !preference.enabled && "opacity-60"
      )}
    >
      {/* Drag handle */}
      <button
        type="button"
        {...attributes}
        {...listeners}
        className={clsx(
          "flex-shrink-0 p-1 rounded",
          "text-[var(--color-text-dim)] hover:text-[var(--color-text-muted)]",
          "cursor-grab active:cursor-grabbing",
          "focus:outline-none focus:ring-2 focus:ring-[var(--accent-needle)]/50"
        )}
      >
        <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path
            strokeLinecap="round"
            strokeLinejoin="round"
            strokeWidth={2}
            d="M4 8h16M4 16h16"
          />
        </svg>
      </button>

      {/* Priority badge */}
      <span
        className={clsx(
          "flex-shrink-0 w-6 h-6 rounded-full",
          "flex items-center justify-center",
          "text-xs font-semibold",
          preference.enabled
            ? "bg-[var(--accent-safe)]/20 text-[var(--accent-safe)]"
            : "bg-zinc-700/50 text-zinc-500"
        )}
      >
        #{index + 1}
      </span>

      {/* Provider icon */}
      <ProviderIcon icon={provider.icon} className="flex-shrink-0 w-5 h-5" />

      {/* Provider name */}
      <span
        className={clsx(
          "flex-1 text-sm font-medium",
          preference.enabled
            ? "text-[var(--color-text-primary)]"
            : "text-[var(--color-text-muted)]"
        )}
      >
        {provider.name}
      </span>

      {/* Enable/disable toggle */}
      <ToggleSwitch
        checked={preference.enabled}
        onChange={() => onToggle(preference.id)}
        size="sm"
      />
    </div>
  );
}

interface ProviderIconProps {
  icon: string;
  className?: string;
}

function ProviderIcon({ icon, className }: ProviderIconProps) {
  const iconMap: Record<string, React.ReactNode> = {
    "youtube-music": (
      <svg className={className} viewBox="0 0 24 24" fill="currentColor">
        <path d="M12 0C5.376 0 0 5.376 0 12s5.376 12 12 12 12-5.376 12-12S18.624 0 12 0zm0 19.104c-3.924 0-7.104-3.18-7.104-7.104S8.076 4.896 12 4.896s7.104 3.18 7.104 7.104-3.18 7.104-7.104 7.104zm0-13.332c-3.432 0-6.228 2.796-6.228 6.228S8.568 18.228 12 18.228s6.228-2.796 6.228-6.228S15.432 5.772 12 5.772zM9.684 15.54V8.46L15.816 12l-6.132 3.54z" />
      </svg>
    ),
    youtube: (
      <svg className={className} viewBox="0 0 24 24" fill="currentColor">
        <path d="M23.498 6.186a3.016 3.016 0 0 0-2.122-2.136C19.505 3.545 12 3.545 12 3.545s-7.505 0-9.377.505A3.017 3.017 0 0 0 .502 6.186C0 8.07 0 12 0 12s0 3.93.502 5.814a3.016 3.016 0 0 0 2.122 2.136c1.871.505 9.376.505 9.376.505s7.505 0 9.377-.505a3.015 3.015 0 0 0 2.122-2.136C24 15.93 24 12 24 12s0-3.93-.502-5.814zM9.545 15.568V8.432L15.818 12l-6.273 3.568z" />
      </svg>
    ),
    soundcloud: (
      <svg className={className} viewBox="0 0 24 24" fill="currentColor">
        <path d="M1.175 12.225c-.051 0-.094.046-.101.1l-.233 2.154.233 2.105c.007.058.05.098.101.098.05 0 .09-.04.099-.098l.255-2.105-.27-2.154c-.006-.057-.047-.1-.098-.1zm-.899.828c-.06 0-.091.037-.104.094L0 14.479l.165 1.308c.014.057.045.094.09.094s.089-.037.099-.094l.225-1.308-.225-1.332c-.01-.057-.045-.094-.09-.094zm1.83-1.229c-.061 0-.12.045-.12.104l-.21 2.563.225 2.458c0 .06.045.104.106.104.061 0 .12-.044.12-.104l.24-2.458-.24-2.563c0-.06-.06-.104-.12-.104zm.945-.089c-.075 0-.135.06-.15.135l-.193 2.64.21 2.544c.016.077.075.138.149.138.075 0 .135-.061.15-.138l.24-2.544-.24-2.64c-.015-.075-.06-.135-.135-.135l-.031.001zm1.155.36c-.005-.09-.075-.149-.159-.149-.09 0-.158.06-.164.149l-.217 2.43.2 2.563c.009.09.075.157.165.157.09 0 .164-.068.164-.157l.227-2.563-.227-2.43zm.809-1.709c-.101 0-.181.09-.181.189l-.21 4.32.227 2.624c0 .09.075.18.165.18.09 0 .18-.09.18-.18l.24-2.624-.24-4.32c0-.1-.08-.19-.18-.19zm1.035.3c-.12 0-.221.101-.221.221l-.18 4.2.18 2.64c0 .12.1.21.21.21.12 0 .226-.09.226-.21l.21-2.64-.21-4.2c0-.12-.1-.22-.21-.22zm1.245-1.11c0-.135-.105-.24-.24-.24-.12 0-.24.105-.24.24l-.21 5.28.21 2.684c0 .135.12.24.24.24.12 0 .24-.105.24-.24l.225-2.684-.225-5.28zm.77-.08c-.12 0-.24.104-.24.24l-.21 5.28.21 2.7c0 .12.12.24.24.24s.24-.12.24-.24l.225-2.7-.225-5.28c0-.135-.12-.24-.24-.24zm1.035-.36c-.135 0-.255.12-.255.255l-.18 5.52.18 2.729c0 .136.12.255.255.255.12 0 .255-.12.255-.255l.21-2.729-.21-5.52c0-.135-.135-.255-.255-.255zm1.02-.45c-.149 0-.27.12-.285.27L8.64 14.399l.165 2.774c.015.149.135.27.285.27.135 0 .27-.135.27-.27l.195-2.774-.195-5.684c-.015-.15-.12-.27-.27-.27zm1.095-.36c-.165 0-.3.135-.315.3l-.18 5.925.18 2.79c.015.165.15.3.315.3.149 0 .3-.135.3-.3l.195-2.79-.195-5.925c0-.165-.135-.3-.3-.3zm1.11-.32c-.18 0-.33.15-.33.33l-.165 5.925.165 2.82c0 .18.15.33.33.33.165 0 .33-.15.33-.33l.18-2.82-.18-5.925c0-.18-.165-.33-.33-.33zm1.095-.09c-.195 0-.345.15-.36.345l-.149 5.685.164 2.834c.015.195.165.36.345.36.195 0 .36-.165.36-.36l.18-2.834-.18-5.685c-.015-.195-.165-.345-.36-.345zm1.08.33c-.209 0-.375.165-.375.375l-.165 5.64.165 2.849c0 .21.165.375.375.375.195 0 .375-.165.375-.375l.18-2.849-.18-5.64c0-.21-.165-.375-.375-.375zm1.095.24c-.225 0-.405.18-.405.405l-.15 5.355.15 2.864c0 .225.18.405.405.405.21 0 .405-.18.405-.405l.165-2.864-.165-5.355c0-.225-.195-.405-.405-.405zm3.735.87c-.36 0-.705.06-1.035.18-.21-2.37-2.175-4.23-4.59-4.23-.57 0-1.125.105-1.635.3-.195.075-.24.15-.24.3v8.985c0 .15.12.285.27.3h7.23c1.695 0 3.06-1.38 3.06-3.06 0-1.695-1.365-3.075-3.06-3.075z" />
      </svg>
    ),
    bandcamp: (
      <svg className={className} viewBox="0 0 24 24" fill="currentColor">
        <path d="M0 18.75l7.437-13.5H24l-7.438 13.5H0z" />
      </svg>
    ),
    piped: (
      <svg className={className} viewBox="0 0 24 24" fill="currentColor">
        <path d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm-2 15l-5-5 1.41-1.41L10 14.17l7.59-7.59L19 8l-9 9z" />
      </svg>
    ),
    spotify: (
      <svg className={className} viewBox="0 0 24 24" fill="currentColor">
        <path d="M12 0C5.4 0 0 5.4 0 12s5.4 12 12 12 12-5.4 12-12S18.66 0 12 0zm5.521 17.34c-.24.359-.66.48-1.021.24-2.82-1.74-6.36-2.101-10.561-1.141-.418.122-.779-.179-.899-.539-.12-.421.18-.78.54-.9 4.56-1.021 8.52-.6 11.64 1.32.42.18.479.659.301 1.02zm1.44-3.3c-.301.42-.841.6-1.262.3-3.239-1.98-8.159-2.58-11.939-1.38-.479.12-1.02-.12-1.14-.6-.12-.48.12-1.021.6-1.141C9.6 9.9 15 10.561 18.72 12.84c.361.181.54.78.241 1.2zm.12-3.36C15.24 8.4 8.82 8.16 5.16 9.301c-.6.179-1.2-.181-1.38-.721-.18-.601.18-1.2.72-1.381 4.26-1.26 11.28-1.02 15.721 1.621.539.3.719 1.02.419 1.56-.299.421-1.02.599-1.559.3z" />
      </svg>
    ),
    musicbrainz: (
      <svg className={className} viewBox="0 0 24 24" fill="currentColor">
        <circle cx="12" cy="12" r="10" />
      </svg>
    ),
    discogs: (
      <svg className={className} viewBox="0 0 24 24" fill="currentColor">
        <path d="M12 0C5.372 0 0 5.372 0 12s5.372 12 12 12 12-5.372 12-12S18.628 0 12 0zm0 22.5C6.201 22.5 1.5 17.799 1.5 12S6.201 1.5 12 1.5 22.5 6.201 22.5 12 17.799 22.5 12 22.5zm0-18c-3.59 0-6.5 2.91-6.5 6.5s2.91 6.5 6.5 6.5 6.5-2.91 6.5-6.5-2.91-6.5-6.5-6.5zm0 11.5c-2.761 0-5-2.239-5-5s2.239-5 5-5 5 2.239 5 5-2.239 5-5 5z" />
      </svg>
    ),
    "music-note": (
      <svg className={className} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={2}>
        <path strokeLinecap="round" strokeLinejoin="round" d="M9 19V6l12-3v13M9 19c0 1.105-1.343 2-3 2s-3-.895-3-2 1.343-2 3-2 3 .895 3 2zm12-3c0 1.105-1.343 2-3 2s-3-.895-3-2 1.343-2 3-2 3 .895 3 2zM9 10l12-3" />
      </svg>
    ),
    genius: (
      <svg className={className} viewBox="0 0 24 24" fill="currentColor">
        <path d="M12.004 0C5.373 0 0 5.373 0 12.004c0 6.63 5.373 12.003 12.004 12.003 6.63 0 12.003-5.373 12.003-12.003C24.007 5.373 18.634 0 12.004 0zm.007 3.29a8.716 8.716 0 018.716 8.717 8.716 8.716 0 01-8.716 8.716 8.716 8.716 0 01-8.716-8.716 8.716 8.716 0 018.716-8.716z" />
      </svg>
    ),
    musixmatch: (
      <svg className={className} viewBox="0 0 24 24" fill="currentColor">
        <path d="M12 0C5.373 0 0 5.373 0 12s5.373 12 12 12 12-5.373 12-12S18.627 0 12 0zm3.895 17.395l-2.79-4.26-2.79 4.26-1.42-1.01 3.21-4.905-3.21-4.905 1.42-1.01 2.79 4.26 2.79-4.26 1.42 1.01-3.21 4.905 3.21 4.905-1.42 1.01z" />
      </svg>
    ),
    azlyrics: (
      <svg className={className} viewBox="0 0 24 24" fill="currentColor">
        <path d="M12 2L2 7l10 5 10-5-10-5zM2 17l10 5 10-5M2 12l10 5 10-5" />
      </svg>
    ),
  };

  return iconMap[icon] || (
    <svg className={className} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={2}>
      <circle cx="12" cy="12" r="10" />
    </svg>
  );
}

export interface SortableProviderListProps {
  preferences: ProviderPreference[];
  providers: ProviderInfo[];
  onReorder: (preferences: ProviderPreference[]) => void;
  onToggle: (id: string) => void;
  label?: string;
  description?: string;
}

export function SortableProviderList({
  preferences,
  providers,
  onReorder,
  onToggle,
  label,
  description,
}: SortableProviderListProps) {
  const sensors = useSensors(
    useSensor(PointerSensor),
    useSensor(KeyboardSensor, {
      coordinateGetter: sortableKeyboardCoordinates,
    })
  );

  // Create a map for quick provider lookup
  const providerMap = new Map(providers.map((p) => [p.id, p]));

  const handleDragEnd = (event: DragEndEvent) => {
    const { active, over } = event;

    if (over && active.id !== over.id) {
      const oldIndex = preferences.findIndex((p) => p.id === active.id);
      const newIndex = preferences.findIndex((p) => p.id === over.id);
      onReorder(arrayMove(preferences, oldIndex, newIndex));
    }
  };

  return (
    <div className="space-y-3">
      {label && (
        <div>
          <label className="text-sm font-medium text-[var(--color-text-secondary)]">
            {label}
          </label>
          {description && (
            <p className="text-xs text-[var(--color-text-muted)] mt-0.5">
              {description}
            </p>
          )}
        </div>
      )}
      <DndContext
        sensors={sensors}
        collisionDetection={closestCenter}
        onDragEnd={handleDragEnd}
      >
        <SortableContext
          items={preferences.map((p) => p.id)}
          strategy={verticalListSortingStrategy}
        >
          <div className="space-y-2">
            {preferences.map((pref, index) => {
              const provider = providerMap.get(pref.id);
              if (!provider) return null;
              return (
                <SortableProviderItem
                  key={pref.id}
                  preference={pref}
                  provider={provider}
                  index={index}
                  onToggle={onToggle}
                />
              );
            })}
          </div>
        </SortableContext>
      </DndContext>
    </div>
  );
}

export default SortableProviderList;
