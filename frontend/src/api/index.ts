// API Client
export { apiClient, getErrorMessage } from "./client";

// Auth
export {
  login,
  register,
  logout,
  getCurrentUser,
  refreshToken,
  changePassword,
  deleteAccount,
  useCurrentUser,
  useLogin,
  useRegister,
  useLogout,
  useRefreshToken,
  useChangePassword,
  useDeleteAccount,
  authKeys,
  type LoginRequest,
  type RegisterRequest,
  type AuthResponse,
  type ChangePasswordRequest,
} from "./auth";

 // Legacy songs export removed

// Legacy matches export removed

// Legacy votes export removed

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
  useInternalArtist,
  useInternalAlbum,
  useInternalPlaylist,
  useInternalSong,
  useUniversalSearch,
  useUniversalSearchMutation,
  refreshEntity,
  useRefreshEntity,
  submitLyrics,
  useSubmitLyrics,
  entityKeys,
} from "./entities";

// Lyrics
export {
  getLyricsForSong,
  useLyrics,
  useRefreshLyrics,
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
