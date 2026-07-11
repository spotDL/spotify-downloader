import { Toaster as SonnerToaster, toast } from "sonner";
import { type ComponentProps, type CSSProperties } from "react";
import { useUiStore } from "../../stores/ui";

export type ToasterProps = ComponentProps<typeof SonnerToaster>;

/**
 * App toaster. Mounted once at the root. Themed to Control Room tokens via
 * sonner's CSS variables so it tracks light/dark automatically; richColors is
 * left off so success/error read in our palette, not sonner's. The light/dark
 * mode follows the ui store's theme (this app has no next-themes).
 */
export function Toaster(props: ToasterProps) {
  const theme = useUiStore((s) => s.theme);

  return (
    <SonnerToaster
      theme={theme}
      position="bottom-right"
      richColors={false}
      closeButton
      toastOptions={{
        classNames: {
          toast:
            "!bg-card !border !border-border !text-foreground !rounded-lg !shadow-lg !font-sans",
          title: "!text-sm !font-medium !text-foreground",
          description: "!text-sm !text-muted-foreground",
          actionButton: "!bg-primary !text-primary-foreground !rounded-md !text-xs",
          cancelButton: "!bg-elevated !text-muted-foreground !rounded-md !text-xs",
          closeButton: "!bg-surface !border-border !text-muted-foreground",
          icon: "!text-muted-foreground",
          error: "!text-destructive [&_[data-icon]]:!text-destructive",
          success: "!text-success [&_[data-icon]]:!text-success",
          warning: "!text-warning [&_[data-icon]]:!text-warning",
          info: "!text-info [&_[data-icon]]:!text-info",
        },
      }}
      style={
        {
          "--normal-bg": "var(--card)",
          "--normal-text": "var(--foreground)",
          "--normal-border": "var(--border)",
        } as CSSProperties
      }
      {...props}
    />
  );
}

export { toast };
