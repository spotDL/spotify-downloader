import { useState } from "react";
import { Link } from "@tanstack/react-router";
import { useSubmitDownload } from "../api/downloads";
import { isApiError } from "../api/errors";
import { toast } from "./Toasts";
import { ActionButton } from "./ActionButton";
import { DownloadIcon } from "./icons";

// The album/playlist "Enqueue all" action: POST /downloads with the bare
// canonical id (the server expands it into N jobs — do NOT prefix a provider
// scheme). On success a toast fires and a persistent link to the queue appears;
// useSubmitDownload already invalidates the downloads cache.
export function EnqueueAllButton({
  query,
  label = "Enqueue all",
}: {
  query: string;
  label?: string;
}) {
  const submit = useSubmitDownload();
  const [enqueued, setEnqueued] = useState(false);

  return (
    <div className="flex flex-col items-start gap-1.5">
      <ActionButton
        icon={<DownloadIcon className="size-4" />}
        disabled={submit.isPending}
        onClick={() =>
          submit.mutate(
            { body: { query } },
            {
              onSuccess: () => {
                setEnqueued(true);
                toast.info("Added to the download queue.");
              },
              onError: (error) => {
                if (isApiError(error)) toast.fromApiError(error);
                else toast.error("Couldn't start the download.");
              },
            },
          )
        }
      >
        {submit.isPending ? "Enqueuing…" : label}
      </ActionButton>
      {enqueued ? (
        <Link
          to="/downloads"
          className="text-xs font-medium text-primary hover:underline"
        >
          View downloads →
        </Link>
      ) : null}
    </div>
  );
}
