import { screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it } from "vitest";

import { renderWithProviders } from "../../test/render";
import { validateSearch, type SearchValues } from "./SearchForm";
import { SearchPage } from "./SearchPage";

const DELHI = { code: "NDLS", name: "New Delhi" };
const MUMBAI = { code: "MMCT", name: "Mumbai Central" };
const TODAY = "2026-11-01";

function values(overrides: Partial<SearchValues> = {}): SearchValues {
  return { from: DELHI, to: MUMBAI, date: "2026-11-02", cls: "", ...overrides };
}

describe("validateSearch", () => {
  it("accepts a complete search", () => {
    expect(validateSearch(values(), TODAY)).toEqual({});
  });

  it("requires both stations and different ones", () => {
    expect(validateSearch(values({ from: null, to: null }), TODAY)).toMatchObject({
      from: expect.any(String),
      to: expect.any(String),
    });
    expect(validateSearch(values({ to: DELHI }), TODAY).to).toMatch(/different/);
  });

  it("limits the date to the reservation window", () => {
    expect(validateSearch(values({ date: "2026-10-31" }), TODAY).date).toMatch(/past/);
    expect(validateSearch(values({ date: "2026-12-31" }), TODAY)).toEqual({});
    expect(validateSearch(values({ date: "2027-01-01" }), TODAY).date).toMatch(/60 days/);
  });
});

describe("SearchPage", () => {
  it("shows the form and reports missing stations on submit", async () => {
    renderWithProviders(<SearchPage />);

    expect(screen.getByRole("heading", { name: "Search trains" })).toBeInTheDocument();
    await userEvent.click(screen.getByRole("button", { name: "Search trains" }));

    expect(screen.getAllByText("Choose a station from the list.")).toHaveLength(2);
  });
});
