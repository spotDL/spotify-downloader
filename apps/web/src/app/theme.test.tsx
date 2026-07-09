import { act } from "react";
import { render } from "@testing-library/react";
import { ThemeProvider } from "./theme";
import { useUiStore } from "../stores/ui";

test("stamps document data-theme from the ui store theme", () => {
  render(
    <ThemeProvider>
      <span>content</span>
    </ThemeProvider>,
  );

  act(() => useUiStore.getState().setTheme("dark"));
  expect(document.documentElement.dataset.theme).toBe("dark");

  act(() => useUiStore.getState().setTheme("light"));
  expect(document.documentElement.dataset.theme).toBe("light");
});
