import { createContext, useContext, useCallback, useRef } from "react";
import { useSettingsStore } from "@/stores/settings";
import type { SettingsData } from "@/stores/settings";
import { useToast } from "@/components/ui";

interface SettingsContextValue {
  /** Update a single setting, show a toast, and trigger auto-save */
  changeSetting: <K extends keyof SettingsData>(key: K, value: SettingsData[K], label: string) => void;
  /** Wrapper for select onChange — extracts value from event */
  changeSelect: <K extends keyof SettingsData>(key: K, label: string) => (e: React.ChangeEvent<HTMLSelectElement>) => void;
  /** Wrapper for text input onChange — debounces the toast */
  changeInput: <K extends keyof SettingsData>(key: K, label: string) => (e: React.ChangeEvent<HTMLInputElement>) => void;
  /** Wrapper for slider onChange */
  changeSlider: <K extends keyof SettingsData>(key: K, label: string) => (value: number) => void;
  /** Trigger auto-save without showing a toast (for custom handlers) */
  triggerAutoSave: () => void;
  /** Show a success toast (for custom handlers) */
  showSuccess: (message: string) => void;
}

const SettingsContext = createContext<SettingsContextValue | null>(null);

export function useSettingsContext(): SettingsContextValue {
  const ctx = useContext(SettingsContext);
  if (!ctx) {
    throw new Error("useSettingsContext must be used within a SettingsProvider");
  }
  return ctx;
}

export function SettingsProvider({
  onPendingSave,
  children,
}: {
  onPendingSave: () => void;
  children: React.ReactNode;
}) {
  const update = useSettingsStore((s) => s.update);
  const { success: showSuccessToast } = useToast();
  const inputTimeouts = useRef<Record<string, ReturnType<typeof setTimeout>>>({});

  const triggerAutoSave = useCallback(() => {
    onPendingSave();
  }, [onPendingSave]);

  const showSuccess = useCallback((message: string) => {
    showSuccessToast(message);
  }, [showSuccessToast]);

  const changeSetting = useCallback(<K extends keyof SettingsData>(key: K, value: SettingsData[K], label: string) => {
    update(key, value);
    showSuccessToast(`${label} updated`);
    onPendingSave();
  }, [update, showSuccessToast, onPendingSave]);

  const changeSelect = useCallback(<K extends keyof SettingsData>(key: K, label: string) => (e: React.ChangeEvent<HTMLSelectElement>) => {
    update(key, e.target.value as SettingsData[K]);
    showSuccessToast(`${label} updated`);
    onPendingSave();
  }, [update, showSuccessToast, onPendingSave]);

  const changeInput = useCallback(<K extends keyof SettingsData>(key: K, label: string) => (e: React.ChangeEvent<HTMLInputElement>) => {
    update(key, e.target.value as SettingsData[K]);
    if (inputTimeouts.current[label]) {
      clearTimeout(inputTimeouts.current[label]);
    }
    inputTimeouts.current[label] = setTimeout(() => {
      showSuccessToast(`${label} updated`);
      onPendingSave();
    }, 500);
  }, [update, showSuccessToast, onPendingSave]);

  const changeSlider = useCallback(<K extends keyof SettingsData>(key: K, label: string) => (value: number) => {
    update(key, value as SettingsData[K]);
    showSuccessToast(`${label} updated`);
    onPendingSave();
  }, [update, showSuccessToast, onPendingSave]);

  return (
    <SettingsContext.Provider value={{ changeSetting, changeSelect, changeInput, changeSlider, triggerAutoSave, showSuccess }}>
      {children}
    </SettingsContext.Provider>
  );
}
