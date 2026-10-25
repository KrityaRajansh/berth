import { describe, expect, it } from "vitest";

import { statusTone } from "../components/StatusBadge";
import { safeNext } from "./auth/LoginPage";
import { validateRegistration } from "./auth/RegisterPage";
import { validatePassenger } from "./booking/PassengerForm";

describe("validatePassenger", () => {
  const valid = { name: "Asha Rao", age: "34", gender: "F" as const, berth_pref: "" as const };

  it("accepts valid details", () => {
    expect(validatePassenger(valid)).toEqual({});
  });

  it.each([
    ["name", { name: "A" }],
    ["name", { name: "<script>" }],
    ["age", { age: "0" }],
    ["age", { age: "121" }],
    ["gender", { gender: "" as const }],
  ])("rejects an invalid %s", (field, patch) => {
    expect(validatePassenger({ ...valid, ...patch })).toHaveProperty(field);
  });
});

describe("validateRegistration", () => {
  const form = {
    full_name: "Kavya Menon",
    email: "kavya@example.com",
    mobile: "9876543210",
    password: "Secur3pass",
    confirm: "Secur3pass",
  };

  it("accepts a valid form", () => {
    expect(validateRegistration(form)).toEqual({});
  });

  it("checks mobile, password strength and confirmation", () => {
    const errors = validateRegistration({
      ...form,
      mobile: "12345",
      password: "onlyletters",
      confirm: "different",
    });
    expect(Object.keys(errors).sort()).toEqual(["confirm", "mobile", "password"]);
  });
});

describe("safeNext", () => {
  it("only allows paths on this site after login", () => {
    expect(safeNext("/bookings")).toBe("/bookings");
    expect(safeNext("https://evil.example")).toBe("/");
    expect(safeNext("//evil.example")).toBe("/");
    expect(safeNext(null)).toBe("/");
  });
});

describe("statusTone", () => {
  it("colours ticket statuses", () => {
    expect(statusTone("CNF/S1/23/LB")).toBe("green");
    expect(statusTone("WL 3")).toBe("amber");
    expect(statusTone("CAN")).toBe("red");
    expect(statusTone("COMPLETED")).toBe("blue");
  });
});
