import { render, screen } from "@testing-library/react";
import App from "./App";

test("renders the spotDL heading", () => {
  render(<App />);
  expect(screen.getByRole("heading", { name: "spotDL" })).toBeDefined();
});
