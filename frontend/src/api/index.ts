// API Client
export { apiClient } from "./client";

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
