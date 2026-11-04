import { expect, request as playwrightRequest, type APIRequestContext, type Page } from "@playwright/test";
import { mkdirSync } from "node:fs";
import { dirname, resolve } from "node:path";
import { fileURLToPath } from "node:url";

export const ADMIN = {
  email: "admin@example.com",
  password: process.env.SEED_ADMIN_PASSWORD ?? "Admin-e2e-123",
};

export const APPROVE_CARD = "4111 1111 1111 1111";
export const DECLINE_CARD = "4000 0000 0000 0002";

const SCREENSHOT_DIR = resolve(dirname(fileURLToPath(import.meta.url)), "../../docs/test/screenshots");

/** Saves a full-page screenshot for the test report when SCREENSHOTS=1. */
export async function evidence(page: Page, name: string) {
  if (!process.env.SCREENSHOTS) return;
  mkdirSync(SCREENSHOT_DIR, { recursive: true });
  await page.screenshot({ path: `${SCREENSHOT_DIR}/${name}.png`, fullPage: true });
}

/** A date in India, `days` from today, as YYYY-MM-DD. */
export function istDate(days: number): string {
  const now = new Date(Date.now() + days * 86_400_000);
  return new Intl.DateTimeFormat("en-CA", { timeZone: "Asia/Kolkata" }).format(now);
}

// Two days ahead is always before the chart cut-off (18:00 the day before departure).
export const TRAVEL_DATE = istDate(2);

export function resultsUrl(from: [string, string], to: [string, string], date = TRAVEL_DATE) {
  const params = new URLSearchParams({
    from: from[0],
    fromName: from[1],
    to: to[0],
    toName: to[1],
    date,
  });
  return `/trains?${params}`;
}

export const DELHI: [string, string] = ["NDLS", "New Delhi"];
export const MUMBAI: [string, string] = ["MMCT", "Mumbai Central"];

export function uniqueSuffix(): string {
  return `${Date.now()}`.slice(-6);
}

export async function register(page: Page, name = "Riya Kapoor") {
  const suffix = uniqueSuffix();
  const email = `riya${suffix}@example.com`;
  await page.goto("/register");
  await page.getByLabel("Full name").fill(name);
  await page.getByLabel("E-mail").fill(email);
  await page.getByLabel("Mobile number").fill(`98${suffix}${Math.floor(Math.random() * 90 + 10)}`);
  await page.getByLabel("Password", { exact: true }).fill("Travel123");
  await page.getByLabel("Confirm password").fill("Travel123");
  await page.getByRole("button", { name: "Create account" }).click();
  await expect(page.getByRole("button", { name: "Log out" })).toBeVisible();
  return { email, password: "Travel123" };
}

export async function login(page: Page, email: string, password: string) {
  await page.goto("/login");
  await page.getByLabel("E-mail").fill(email);
  await page.getByLabel("Password").fill(password);
  await page.getByRole("button", { name: "Log in" }).click();
  await expect(page.getByRole("button", { name: "Log out" })).toBeVisible();
}

export async function fillPassenger(
  page: Page,
  index: number,
  p: { name: string; age: number; gender: "Female" | "Male" },
) {
  await page.getByLabel(`Passenger ${index + 1} name`).fill(p.name);
  await page.getByLabel("Age").nth(index).fill(String(p.age));
  await page.getByLabel("Gender").nth(index).selectOption({ label: p.gender });
}

/** From the results page: books `cls` on `train` for the given passengers and pays. */
export async function bookAndPay(
  page: Page,
  train: string,
  cls: string,
  passengers: { name: string; age: number; gender: "Female" | "Male" }[],
  card = APPROVE_CARD,
) {
  await page.getByRole("button", { name: `Book ${cls} on ${train}` }).click();
  await expect(page.getByRole("heading", { name: "Passenger details" })).toBeVisible();
  for (let i = 0; i < passengers.length; i++) {
    if (i > 0) await page.getByRole("button", { name: "Add passenger" }).click();
    await fillPassenger(page, i, passengers[i]);
  }
  await page.getByRole("button", { name: "Continue to payment" }).click();
  await expect(page.getByRole("heading", { name: "Payment" })).toBeVisible();
  await page.getByLabel("Card number").fill(card);
  await page.getByRole("button", { name: /^Pay / }).click();
}

/** An API client logged in as the administrator, for test setup. */
export async function adminApi(baseURL: string): Promise<APIRequestContext> {
  const api = await playwrightRequest.newContext({ baseURL });
  const login = await api.post("/api/v1/auth/login", { data: ADMIN });
  expect(login.ok()).toBe(true);
  return api;
}

/**
 * Creates a small daily train from New Delhi to a new station, with one Sleeper coach
 * of `berths` berths, and opens bookings. Used where a scenario needs a nearly full train.
 */
export async function createSmallTrain(api: APIRequestContext, berths: number) {
  const suffix = uniqueSuffix();
  const code = `Y${[...suffix.slice(-3)].map((d) => String.fromCharCode(65 + Number(d))).join("")}`;
  const number = `5${suffix.slice(-4)}`;
  const ok = async (response: Promise<import("@playwright/test").APIResponse>) => {
    const r = await response;
    expect(r.ok(), await r.text()).toBe(true);
    return r;
  };
  await ok(api.post("/api/v1/admin/stations", { data: { code, name: `Halt ${code}`, city: "Test" } }));
  await ok(
    api.post("/api/v1/admin/trains", {
      data: { number, name: "Short Hop Passenger", running_days: [0, 1, 2, 3, 4, 5, 6] },
    }),
  );
  await ok(
    api.put(`/api/v1/admin/trains/${number}/route`, {
      data: [
        { station_code: "NDLS", departure: "10:00", day_offset: 0, distance_km: 0 },
        { station_code: code, arrival: "12:00", day_offset: 0, distance_km: 120 },
      ],
    }),
  );
  await ok(
    api.put(`/api/v1/admin/trains/${number}/coaches`, {
      data: [{ code: "S1", travel_class: "SL", berth_count: berths }],
    }),
  );
  await ok(
    api.post("/api/v1/admin/runs/generate", {
      data: { start: istDate(0), end: istDate(10), train_number: number },
    }),
  );
  return { number, station: [code, `Halt ${code}`] as [string, string] };
}

export async function hasNoHorizontalScroll(page: Page): Promise<boolean> {
  return page.evaluate(
    () => document.documentElement.scrollWidth <= document.documentElement.clientWidth,
  );
}
