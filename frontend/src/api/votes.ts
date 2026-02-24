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

interface RelationVoteResponse {
  relation_id: string;
  upvotes: number;
  downvotes: number;
  net_votes: number;
  confidence: number;
  user_vote: "up" | "down" | null;
}

function mapVoteSummary(data: RelationVoteResponse): VoteResponse {
  return {
    match_id: data.relation_id,
    upvotes: data.upvotes,
    downvotes: data.downvotes,
    score: data.net_votes,
    confidence: data.confidence,
    user_vote: data.user_vote,
  };
}

// API functions
export async function createVote(data: CreateVoteRequest): Promise<VoteResponse> {
  const response = await apiClient.post<RelationVoteResponse>(
    `/relations/${data.match_id}/vote`,
    { vote: data.vote_type }
  );
  return mapVoteSummary(response.data);
}

export async function deleteVote(matchId: string): Promise<void> {
  await apiClient.post(`/relations/${matchId}/vote`, { vote: "remove" });
}

export async function getMatchVotes(matchId: string): Promise<VoteSummary> {
  const response = await apiClient.get<RelationVoteResponse>(`/relations/${matchId}/vote`);
  return {
    match_id: response.data.relation_id,
    upvotes: response.data.upvotes,
    downvotes: response.data.downvotes,
    user_vote: response.data.user_vote,
  };
}

export async function getUserVotes(): Promise<UserVoteItem[]> {
  return [];
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
    staleTime: 1000 * 30,
  });
}

export function useUserVotes() {
  return useQuery({
    queryKey: voteKeys.userVotes(),
    queryFn: getUserVotes,
    staleTime: 1000 * 60 * 5,
  });
}

export function useCreateVote() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: createVote,
    onSuccess: (vote) => {
      queryClient.invalidateQueries({ queryKey: voteKeys.match(vote.match_id) });
      queryClient.invalidateQueries({ queryKey: matchKeys.detail(vote.match_id) });
      queryClient.invalidateQueries({ queryKey: voteKeys.userVotes() });
    },
  });
}

export function useDeleteVote() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: deleteVote,
    onSuccess: () => {
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
    if (voteSummary?.user_vote === type) {
      await deleteVoteMutation.mutateAsync(matchId);
      return;
    }
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
