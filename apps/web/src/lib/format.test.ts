import { describe, expect, it } from "vitest";

import {
  addDays,
  formatDate,
  formatDuration,
  formatInr,
  formatTime,
  sameIstDay,
  todayIst,
} from "./format";

describe("format helpers", () => {
  it("formats paise as rupees, showing paise only when present", () => {
    expect(formatInr(546_00)).toBe("₹546");
    expect(formatInr(1354_50)).toBe("₹1,354.50");
    expect(formatInr(1806_00)).toBe("₹1,806");
  });

  it("shows times and dates in IST regardless of the browser's zone", () => {
    const utc = "2026-11-02T00:30:00Z"; // 06:00 IST
    expect(formatTime(utc)).toBe("06:00");
    expect(formatDate("2026-11-02")).toBe("Mon, 2 Nov");
    expect(todayIst(new Date("2026-11-01T19:00:00Z"))).toBe("2026-11-02");
  });

  it("formats durations", () => {
    expect(formatDuration(715)).toBe("11h 55m");
    expect(formatDuration(45)).toBe("45m");
  });

  it("does date arithmetic across months", () => {
    expect(addDays("2026-10-31", 1)).toBe("2026-11-01");
    expect(addDays("2026-11-01", -1)).toBe("2026-10-31");
  });

  it("compares calendar days in IST", () => {
    expect(sameIstDay("2026-11-02T22:00:00+05:30", "2026-11-03T21:00:00+05:30")).toBe(false);
    expect(sameIstDay("2026-11-02T06:00:00+05:30", "2026-11-02T20:00:00+05:30")).toBe(true);
  });
});
