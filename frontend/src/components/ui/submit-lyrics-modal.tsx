import { useState } from "react";
import { Modal } from "@/components/ui/modal";
import { Button } from "@/components/ui/button";

interface SubmitLyricsModalProps {
  isOpen: boolean;
  onClose: () => void;
  onSubmit: (data: { source: string; lyricsText: string; lyricsSynced?: string | null }) => void;
  isSubmitting: boolean;
}

export function SubmitLyricsModal({
  isOpen,
  onClose,
  onSubmit,
  isSubmitting,
}: SubmitLyricsModalProps) {
  const [source, setSource] = useState("user");
  const [lyricsText, setLyricsText] = useState("");
  const [lyricsSynced, setLyricsSynced] = useState("");

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!lyricsText.trim()) return;
    onSubmit({
      source: source.trim() || "user",
      lyricsText: lyricsText.trim(),
      lyricsSynced: lyricsSynced.trim() || null,
    });
  };

  const footer = (
    <>
      <Button type="button" variant="secondary" onClick={onClose}>
        Cancel
      </Button>
      <Button
        type="button"
        variant="primary"
        disabled={isSubmitting || !lyricsText.trim()}
        onClick={handleSubmit}
      >
        {isSubmitting ? "Submitting..." : "Submit Lyrics"}
      </Button>
    </>
  );

  return (
    <Modal
      isOpen={isOpen}
      onClose={onClose}
      title="Submit Lyrics"
      description="Add lyrics from another source or provide your own translation."
      size="lg"
      footer={footer}
    >
      <form onSubmit={handleSubmit} className="space-y-4">
        <div className="space-y-2">
          <label htmlFor="source" className="text-sm font-medium">Source / Provider Name</label>
          <input
            id="source"
            type="text"
            value={source}
            onChange={(e) => setSource(e.target.value)}
            placeholder="e.g. My Translation, AnimeLyrics, etc."
            className="w-full px-3 py-2 bg-zinc-900 border border-zinc-800 rounded-lg focus:outline-none focus:border-accent-cool text-sm"
            required
          />
        </div>

        <div className="space-y-2">
          <label htmlFor="lyricsText" className="text-sm font-medium">Plain Text Lyrics *</label>
          <textarea
            id="lyricsText"
            value={lyricsText}
            onChange={(e) => setLyricsText(e.target.value)}
            placeholder="Paste the plain text lyrics here..."
            className="w-full px-3 py-2 bg-zinc-900 border border-zinc-800 rounded-lg focus:outline-none focus:border-accent-cool text-sm font-mono whitespace-pre resize-y"
            rows={8}
            required
          />
        </div>

        <div className="space-y-2">
          <label htmlFor="lyricsSynced" className="text-sm font-medium">Synced Lyrics (LRC) (Optional)</label>
          <textarea
            id="lyricsSynced"
            value={lyricsSynced}
            onChange={(e) => setLyricsSynced(e.target.value)}
            placeholder="[00:12.34] Example synced lyric verse..."
            className="w-full px-3 py-2 bg-zinc-900 border border-zinc-800 rounded-lg focus:outline-none focus:border-accent-cool text-sm font-mono whitespace-pre resize-y"
            rows={6}
          />
        </div>
      </form>
    </Modal>
  );
}
