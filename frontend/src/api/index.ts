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
  resolveSong,
  searchSongs,
  getSong,
  useResolveSong,
  useSearchSongs,
  useSong,
  useResolveSongMutation,
  songKeys,
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
