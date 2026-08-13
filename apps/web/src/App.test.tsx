import "@testing-library/jest-dom/vitest";
import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { App } from "./App";

describe("App", () => {
  it("states the current stage without claiming unavailable capability", () => {
    render(<App />);

    expect(screen.getByText(/阶段 -1/)).toBeInTheDocument();
    expect(screen.getByText("真实 LLM")).toBeInTheDocument();
    expect(screen.getByText("未启用")).toBeInTheDocument();
  });
});
