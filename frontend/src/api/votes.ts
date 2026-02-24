import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { apiClient } from "./client";
import { matchKeys } from "./matches";

// Types
export interface CreateVoteRequest {
  match_id: string;
  vote_type: "up" | "down";
}

export interface VoteSummary {
  match_id: string;
  upvotes: number;
  downvotes: number;
  user_vote: "up" | "down" | null;
}

export interface VoteResponse extends VoteSummary {
  score: number;
  confidence: number;
}

export interface UserVoteItem {
  match_id: string;
  vote_type: "up" | "down";
  created_at: string;
}

export interface UserVotesResponse {
  votes: UserVoteItem[];
}

// API functions
export async function createVote(data: CreateVoteRequest): Promise<VoteResponse> {
  const response = await apiClient.post<VoteResponse>("/votes", data);
  return response.data;
}

export async function deleteVote(matchId: string): Promise<void> {
  await apiClient.delete(`/votes/${matchId}`);
}

export async function getMatchVotes(matchId: string): Promise<VoteSummary> {
  const response = await apiClient.get<VoteSummary>(`/matches/${matchId}/votes`);
  return response.data;
}

export async function getUserVotes(): Promise<UserVoteItem[]> {
  const response = await apiClient.get<UserVotesResponse>("/votes/me");
  return response.data.votes;
}

// Query keys
export const voteKeys = {
  all: ["votes"] as const,
  lists: () => [...voteKeys.all, "list"] as const,
  userVotes: () => [...voteKeys.lists(), "user"] as const,
  match: (matchId: string) => [...voteKeys.all, "match", matchId] as const,
};

// Hooks
export function useMatchVotes(matchId: string) {
  return useQuery({
    queryKey: voteKeys.match(matchId),
    queryFn: () => getMatchVotes(matchId),
    enabled: !!matchId,
    staleTime: 1000 * 60, // 1 minute
  });
}

export function useUserVotes() {
  return useQuery({
    queryKey: voteKeys.userVotes(),
    queryFn: getUserVotes,
    staleTime: 1000 * 60 * 5, // 5 minutes
  });
}

export function useCreateVote() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: createVote,
    onSuccess: (vote) => {
      // Invalidate the match votes cache
      queryClient.invalidateQueries({
        queryKey: voteKeys.match(vote.match_id),
      });
      // Invalidate the match itself (upvotes/downvotes count)
      queryClient.invalidateQueries({
        queryKey: matchKeys.detail(vote.match_id),
      });
      // Invalidate user votes
      queryClient.invalidateQueries({
        queryKey: voteKeys.userVotes(),
      });
    },
  });
}

export function useDeleteVote() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: deleteVote,
    onSuccess: () => {
      // Invalidate all vote-related queries
      queryClient.invalidateQueries({ queryKey: voteKeys.all });
      queryClient.invalidateQueries({ queryKey: matchKeys.all });
    },
  });
}

// Helper hook to vote on a match
export function useVote(matchId: string) {
  const createVoteMutation = useCreateVote();
  const deleteVoteMutation = useDeleteVote();
  const { data: voteSummary } = useMatchVotes(matchId);

  const vote = async (type: "up" | "down") => {
    // If user already voted the same way, remove the vote
    if (voteSummary?.user_vote === type) {
      await deleteVoteMutation.mutateAsync(matchId);
      return;
    }

    // Create or change vote
    await createVoteMutation.mutateAsync({
      match_id: matchId,
      vote_type: type,
    });
  };

  const removeVote = async () => {
    if (voteSummary?.user_vote) {
      await deleteVoteMutation.mutateAsync(matchId);
    }
  };

  return {
    vote,
    removeVote,
    voteSummary,
    isLoading: createVoteMutation.isPending || deleteVoteMutation.isPending,
    userVote: voteSummary?.user_vote ?? null,
  };
}
