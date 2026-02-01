// API Client
export { apiClient, getErrorMessage } from "./client";

// Auth
export {
  login,
  register,
  logout,
  getCurrentUser,
  refreshToken,
  useCurrentUser,
  useLogin,
  useRegister,
  useLogout,
  useRefreshToken,
  authKeys,
  type LoginRequest,
  type RegisterRequest,
  type AuthResponse,
} from "./auth";

// Songs
export {
  resolveSongUrl,
  searchSongs,
  searchAllPlatforms,
  getSong,
  isValidUrl,
  useResolveSong,
  useSearchSongs,
  useSearchAllPlatforms,
  useSong,
  useResolveSongMutation,
  useSearchSongsMutation,
  useSearchAllPlatformsMutation,
  songKeys,
  type SearchResponse,
  type ResolveResponse,
  type PlatformSearchResult,
  type MultiPlatformSearchResponse,
} from "./songs";

// Matches
export {
  findMatches,
  getMatch,
  submitMatch,
  getMatchesForSong,
  useFindMatches,
  useMatch,
  useMatchesForSong,
  useFindMatchesMutation,
  useSubmitMatch,
  matchKeys,
  type SubmitMatchRequest,
} from "./matches";

// Votes
export {
  createVote,
  deleteVote,
  getMatchVotes,
  getUserVotes,
  useMatchVotes,
  useUserVotes,
  useCreateVote,
  useDeleteVote,
  useVote,
  voteKeys,
  type CreateVoteRequest,
  type VoteSummary,
} from "./votes";

// Health
export { checkHealth, useHealth, healthKeys } from "./health";

// Settings
export {
  getUserSettings,
  updateUserSettings,
  resetUserSettings,
  exportUserSettings,
  importUserSettings,
  useUserSettings,
  useUpdateUserSettings,
  useResetUserSettings,
  useExportUserSettings,
  useImportUserSettings,
  apiToStoreSettings,
  storeToApiSettings,
  settingsKeys,
  type UserSettingsResponse,
} from "./settings";

// Downloads
export {
  startDownload,
  getDownloadStatus,
  listDownloads,
  cancelDownload,
  getDownloadFileUrl,
  useDownloadList,
  useDownloadStatus,
  useStartDownload,
  useCancelDownload,
  downloadKeys,
  type StartDownloadRequest,
  type StartDownloadResponse,
  type DownloadProgress,
  type DownloadListResponse,
} from "./download";

// Entities
export {
  getArtistById,
  getAlbumById,
  getPlaylistById,
  getSongById,
  universalSearch,
  universalSearchGet,
  getSongMetadataSources,
  useInternalArtist,
  useInternalAlbum,
  useInternalPlaylist,
  useInternalSong,
  useUniversalSearch,
  useUniversalSearchMutation,
  useMetadataSources,
  entityKeys,
  type MetadataSnapshotResponse,
  type MetadataSourcesResponse,
} from "./entities";

// Lyrics
export {
  getLyricsForSong,
  searchLyrics,
  useLyrics,
  useRefreshLyrics,
  useSearchLyrics,
  hasLyrics,
  toLyrics,
  lyricsKeys,
  type LyricsResponse,
  type LyricsNotFoundResponse,
} from "./lyrics";

// Metadata Reports
export {
  createReport,
  getMyReports,
  listReports,
  getReport,
  updateReport,
  deleteReport,
  useCreateReport,
  useMyReports,
  useReportsList,
  useReport,
  useUpdateReport,
  useDeleteReport,
  toMetadataReport,
  reportKeys,
  type ReportResponse,
  type ReportListResponse,
  type UpdateReportRequest,
} from "./reports";

// Admin
export {
  listAdminUsers,
  getAdminUser,
  updateAdminUser,
  listAdminMatches,
  updateMatchStatus,
  getSystemStats,
  importMatches,
  importUrls,
  purgeUnverifiedMatches,
  resetDatabase,
  exportMatches,
  exportUsers,
  exportStatistics,
  useAdminUsers,
  useAdminUser,
  useUpdateAdminUser,
  useAdminMatches,
  useUpdateMatchStatus,
  useSystemStats,
  useImportMatches,
  useImportUrls,
  usePurgeUnverifiedMatches,
  useResetDatabase,
  useExportMatches,
  useExportUsers,
  useExportStatistics,
  adminKeys,
  type MatchStatus,
  type UpdateUserRequest,
  type UpdateMatchStatusRequest,
  type ImportMatchesRequest,
  type BulkUrlImportRequest,
  type MatchExportResponse,
  type UserExportResponse,
  type StatisticsExportResponse,
} from "./admin";

// Providers
export {
  getProviders,
  getDefaultProviderPreferences,
  useProviders,
  useDefaultProviderPreferences,
  providerKeys,
  type ProviderInfo as ApiProviderInfo,
  type ProvidersResponse,
  type DefaultPreferencesResponse,
} from "./providers";
