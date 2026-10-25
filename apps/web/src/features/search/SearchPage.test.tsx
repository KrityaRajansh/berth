import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { SearchPage } from "./SearchPage";

describe("SearchPage", () => {
  it("shows the page heading", () => {
    render(<SearchPage />);

    expect(screen.getByRole("heading", { name: "Search trains" })).toBeInTheDocument();
  });
});
