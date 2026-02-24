export { Button, type ButtonProps } from "./button";
export { Input, type InputProps } from "./input";
export { Select, type SelectProps, type SelectOption } from "./select";
export {
  Card,
  CardHeader,
  CardTitle,
  CardDescription,
  CardContent,
  CardFooter,
  type CardProps,
} from "./card";
export { Badge, PlatformBadge, type BadgeProps, type PlatformBadgeProps } from "./badge";
export {
  Table,
  TableHeader,
  TableBody,
  TableFooter,
  TableRow,
  TableHead,
  TableCell,
  TableCaption,
} from "./table";
export {
  Spinner,
  Loading,
  WaveformLoader,
  EqualizerLoader,
  Skeleton,
  type SpinnerProps,
  type LoadingProps,
  type SkeletonProps,
} from "./spinner";

// New Hi-Fi Collector Components
export { CoverArt, type CoverArtProps } from "./cover-art";
export { MatchScoreGauge, MatchScoreBar, ScoreBadge, type MatchScoreGaugeProps, type MatchScoreBarProps, type ScoreBadgeProps } from "./match-gauge";
export { Modal, ConfirmModal, type ModalProps, type ConfirmModalProps } from "./modal";
export { ToastProvider, useToast } from "./toast";
export { ToggleSwitch, type ToggleSwitchProps } from "./toggle-switch";
export { Slider, RangeSlider, type SliderProps, type RangeSliderProps } from "./slider";
export { DataTable, Pagination, type DataTableProps, type PaginationProps } from "./data-table";
export { StatCard, StatCardGrid, StatInline, type StatCardProps, type StatInlineProps } from "./stat-card";
export { LyricsDisplay, type LyricsDisplayProps } from "./lyrics-display";
export { MetadataSourceBadge, MetadataField, MetadataGrid, MetadataPanel, type MetadataSourceBadgeProps, type MetadataFieldProps, type MetadataGridProps, type MetadataPanelProps } from "./metadata-source-badge";
export { PlatformLink, PlatformLinksGrid, type PlatformLinkProps, type PlatformLinksGridProps } from "./platform-link";
export { ReportModal, ReportButton, type ReportModalProps, type ReportButtonProps } from "./report-modal";

// Audio & Metadata Components
export {
  KeySignatureBadge,
  getKeySignatureString,
  getAlternateKeyName,
  type KeySignatureBadgeProps,
} from "./key-signature-badge";
export {
  TempoVisualizer,
  TempoLabel,
  getTempoName,
  type TempoVisualizerProps,
  type TempoLabelProps,
} from "./tempo-visualizer";
export {
  AudioFeaturesPanel,
  AudioFeaturesSummary,
  SingleFeature,
  type AudioFeaturesPanelProps,
  type AudioFeaturesSummaryProps,
  type SingleFeatureProps,
} from "./audio-features-panel";
export {
  TrackInfoGrid,
  TrackInfoRow,
  MiniTrackCard,
  type TrackInfoGridProps,
  type TrackInfoRowProps,
  type MiniTrackCardProps,
} from "./track-info-grid";

// Navigation & Entity Components
export {
  DiscographyGrid,
  type DiscographyGridProps,
  type AlbumSummaryWithType,
} from "./discography-grid";
export {
  RelatedArtistsCarousel,
  type RelatedArtistsCarouselProps,
} from "./related-artists-carousel";
export {
  TrackRow,
  TrackRowList,
  type TrackRowProps,
  type TrackRowListProps,
} from "./track-row";
export {
  EntityBreadcrumb,
  EntityBreadcrumbPreset,
  type EntityBreadcrumbProps,
  type EntityBreadcrumbPresetProps,
} from "./entity-breadcrumb";

// Connection Status
export {
  ConnectionStatusCompact,
  ConnectionStatusDetailed,
} from "./connection-status";

// Provider Settings
export {
  SortableProviderList,
  type SortableProviderListProps,
  type ProviderPreference,
  type ProviderInfo,
} from "./sortable-provider-list";

// Metadata Source Selector
export {
  MetadataSourceSelector,
  type MetadataSourceSelectorProps,
  type MetadataSnapshot,
} from "./metadata-source-selector";

// Refresh Metadata Button
export { RefreshMetadataButton } from "./refresh-metadata-button";

// Entity Error Card
export {
  EntityErrorCard,
  classifyEntityError,
  type EntityErrorKind,
  type ClassifiedEntityError,
} from "./entity-error-card";
