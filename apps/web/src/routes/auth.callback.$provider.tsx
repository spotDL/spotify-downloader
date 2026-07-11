import { useEffect, useRef } from "react";
import { createFileRoute, useNavigate } from "@tanstack/react-router";
import { useQueryClient } from "@tanstack/react-query";
import { motion, useReducedMotion } from "motion/react";
import {
  consumeOauthFragment,
  invalidateMe,
  oauthErrorMessage,
} from "../api/mutations";
import { toast } from "../components/Toasts";
import { Spinner } from "../components/Spinner";

// CONTRACT C — the OAuth return. Reads the token pair (or `#error`) from the URL
// FRAGMENT only, stores tokens, strips the fragment via history.replaceState so
// they never persist in the URL bar / history, then navigates.
export const Route = createFileRoute("/auth/callback/$provider")({
  component: OauthCallbackPage,
});

function Wordmark() {
  return (
    <div className="text-center">
      <span className="font-display text-3xl font-bold tracking-tight">
        <span className="text-foreground">spot</span>
        <span className="text-primary">DL</span>
      </span>
    </div>
  );
}

function OauthCallbackPage() {
  const navigate = useNavigate();
  const reduceMotion = useReducedMotion();
  const queryClient = useQueryClient();
  // StrictMode double-invokes effects; guard so the fragment is consumed once.
  const consumedRef = useRef(false);

  useEffect(() => {
    if (consumedRef.current) return;
    consumedRef.current = true;

    const outcome = consumeOauthFragment(window.location.hash);
    // Strip the fragment immediately — before any navigation settles — so tokens
    // never linger in the URL bar, browser history, or session restore.
    window.history.replaceState(
      null,
      "",
      window.location.pathname + window.location.search,
    );

    if (outcome.kind === "success") {
      void invalidateMe(queryClient);
      void navigate({ to: "/" });
      return;
    }
    if (outcome.kind === "error") {
      const { message, severity } = oauthErrorMessage(outcome.code);
      toast.push(message, severity);
      void navigate({ to: "/login" });
      return;
    }
    toast.error("Sign-in failed — the callback was missing its tokens.");
    void navigate({ to: "/login" });
  }, [navigate, queryClient]);

  return (
    <div className="flex min-h-[60vh] items-center justify-center">
      <motion.div
        initial={reduceMotion ? false : { opacity: 0, y: 8 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.3, ease: [0.16, 1, 0.3, 1] }}
        className="mx-auto w-full max-w-sm space-y-6"
      >
        <Wordmark />
        <div className="flex flex-col items-center gap-3 rounded-lg border border-border bg-card p-8 text-center">
          <Spinner label="Completing sign-in" className="size-6" />
          <p className="text-sm text-muted-foreground">Signing you in…</p>
        </div>
      </motion.div>
    </div>
  );
}
