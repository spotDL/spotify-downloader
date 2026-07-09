/* eslint-disable */
// @generated
// This file is auto-generated from apps/server/ws-protocol.json by
// scripts/gen-ws-types.mjs. Do NOT edit by hand — run `make web-clients`.

export type WsMessage = (WsHello | WsJobQueued | WsJobStarted | WsProgress | WsJobFinished | WsJobFailed | WsJobCancelled | WsBatchFinished)
export type ProtocolVersion = number
export type Type = "hello"
export type BatchId = (string | null)
export type JobId = string
export type ListLength = (number | null)
export type ListPosition = (number | null)
export type TrackName = (string | null)
export type Type1 = "job_queued"
export type BatchId1 = (string | null)
export type JobId1 = string
export type Type2 = "job_started"
export type BatchId2 = (string | null)
export type JobId2 = string
export type Overall = number
export type Percent = (number | null)
export type Phase = string
export type Type3 = "progress"
export type BatchId3 = (string | null)
export type JobId3 = string
export type OutputPath = (string | null)
export type SkipReason = (string | null)
export type Skipped = boolean
export type Status = "completed"
export type Type4 = "job_finished"
export type BatchId4 = (string | null)
export type Error = (string | null)
export type JobId4 = string
export type Step = (string | null)
export type Type5 = "job_failed"
export type BatchId5 = (string | null)
export type JobId5 = string
export type Type6 = "job_cancelled"
export type BatchId6 = string
export type Cancelled = number
export type Completed = number
export type Failed = number
export type M3UPaths = string[]
export type SaveFilePath = (string | null)
export type Skipped1 = number
export type Type7 = "batch_finished"

/**
 * First frame sent to every client immediately after accept — the protocol
 * version envelope. Clients reject a version they don't support.
 */
export interface WsHello {
protocol_version?: ProtocolVersion
type?: Type
}
export interface WsJobQueued {
batch_id: BatchId
job_id: JobId
list_length: ListLength
list_position: ListPosition
track_name: TrackName
type?: Type1
}
export interface WsJobStarted {
batch_id: BatchId1
job_id: JobId1
type?: Type2
}
export interface WsProgress {
batch_id: BatchId2
job_id: JobId2
overall: Overall
percent: Percent
phase: Phase
type?: Type3
}
export interface WsJobFinished {
batch_id: BatchId3
job_id: JobId3
output_path: OutputPath
skip_reason: SkipReason
skipped: Skipped
status: Status
type?: Type4
}
export interface WsJobFailed {
batch_id: BatchId4
error: Error
job_id: JobId4
step: Step
type?: Type5
}
export interface WsJobCancelled {
batch_id: BatchId5
job_id: JobId5
type?: Type6
}
export interface WsBatchFinished {
batch_id: BatchId6
cancelled: Cancelled
completed: Completed
failed: Failed
m3u_paths: M3UPaths
save_file_path: SaveFilePath
skipped: Skipped1
type?: Type7
}
