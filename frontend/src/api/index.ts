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
  getSong,
  isValidUrl,
  useResolveSong,
  useSearchSongs,
  useSong,
  useResolveSongMutation,
  useSearchSongsMutation,
  songKeys,
  type SearchResponse,
  type ResolveResponse,
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
