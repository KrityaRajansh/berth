import AxeBuilder from "@axe-core/playwright";
import { expect, test, type Page } from "@playwright/test";

import {
  DELHI,
  MUMBAI,
  TRAVEL_DATE,
  adminApi,
  bookAndPay,
  createSmallTrain,
  uniqueSuffix,
  evidence,
  fillPassenger,
  hasNoHorizontalScroll,
  register,
  resultsUrl,
} from "./helpers";

async function seriousViolations(page: Page) {
  const results = await new AxeBuilder({ page }).withTags(["wcag2a", "wcag2aa"]).analyze();
  return results.violations
    .filter((v) => v.impact === "serious" || v.impact === "critical")
    .map((v) => `${v.id}: ${v.nodes.map((n) => n.target.join(" ")).join(", ")}`);
}

test("ST-13 key pages have no serious accessibility violations", async ({ page }) => {
  const checked: Record<string, string[]> = {};
  await page.goto("/");
  checked.search = await seriousViolations(page);

  await page.goto(resultsUrl(DELHI, MUMBAI));
  await expect(page.getByRole("article").first()).toBeVisible();
  checked.results = await seriousViolations(page);

  await register(page, "Asha Rao");
  checked.account = await seriousViolations(page);
  await page.goto(resultsUrl(DELHI, MUMBAI));
  await page.getByRole("button", { name: "Book SL on 22401" }).click();
  await expect(page.getByRole("heading", { name: "Passenger details" })).toBeVisible();
  checked.passengers = await seriousViolations(page);

  await fillPassenger(page, 0, { name: "Asha Rao", age: 34, gender: "Female" });
  await page.getByRole("button", { name: "Continue to payment" }).click();
  await expect(page.getByRole("heading", { name: "Payment" })).toBeVisible();
  checked.payment = await seriousViolations(page);

  await page.getByLabel("Card number").fill("4111 1111 1111 1111");
  await page.getByRole("button", { name: /^Pay / }).click();
  await expect(page.getByRole("heading", { name: /^PNR / })).toBeVisible();
  checked.confirmation = await seriousViolations(page);

  await page.goto("/bookings");
  checked.myBookings = await seriousViolations(page);

  expect(checked).toEqual({
    search: [],
    results: [],
    account: [],
    passengers: [],
    payment: [],
    confirmation: [],
    myBookings: [],
  });
});

test.describe("ST-08 small screens", () => {
  test.use({ viewport: { width: 360, height: 780 } });

  test("the booking flow works at 360 px without sideways scrolling", async ({ page }) => {
    await page.goto("/");
    expect(await hasNoHorizontalScroll(page)).toBe(true);
    await register(page, "Neel Shah");
    expect(await hasNoHorizontalScroll(page)).toBe(true);

    await page.goto(resultsUrl(DELHI, MUMBAI));
    await expect(page.getByRole("article").first()).toBeVisible();
    expect(await hasNoHorizontalScroll(page)).toBe(true);
    await evidence(page, "st08-mobile-results");

    await bookAndPay(page, "22401", "SL", [{ name: "Neel Shah", age: 22, gender: "Male" }]);
    await expect(page.getByRole("heading", { name: /^PNR \d{10}$/ })).toBeVisible();
    expect(await hasNoHorizontalScroll(page)).toBe(true);
    await evidence(page, "st08-mobile-confirmation");
  });
});

test("ST-09 twenty parallel payments for the last berth confirm exactly one", async ({
  playwright,
}) => {
  const base = process.env.E2E_BASE_URL ?? "http://localhost:5173";
  const admin = await adminApi(base);
  const train = await createSmallTrain(admin, 1);
  await admin.dispose();

  const user = await playwright.request.newContext({ baseURL: base });
  const suffix = uniqueSuffix();
  const registered = await user.post("/api/v1/auth/register", {
    data: {
      full_name: "Load Tester",
      email: `load${suffix}@example.com`,
      mobile: `97${suffix}11`,
      password: "Travel123",
    },
  });
  expect(registered.ok()).toBe(true);
  const results = await (
    await user.get("/api/v1/trains/search", {
      params: { from: "NDLS", to: train.station[0], date: TRAVEL_DATE },
    })
  ).json();
  const runId = results[0].run_id;

  const ids: string[] = [];
  for (let i = 0; i < 20; i++) {
    const created = await user.post("/api/v1/bookings", {
      data: {
        run_id: runId,
        travel_class: "SL",
        from_code: "NDLS",
        to_code: train.station[0],
        passengers: [{ name: "Racer", age: 30, gender: "M" }],
      },
    });
    ids.push((await created.json()).id);
  }

  const paid = await Promise.all(
    ids.map((id) =>
      user.post(`/api/v1/bookings/${id}/payments`, {
        data: { method: "card", card_number: "4111111111111111" },
      }),
    ),
  );
  expect(paid.map((r) => r.status())).toEqual(Array(20).fill(200));

  const statuses = await Promise.all(
    paid.map(async (r) => (await r.json()).passengers[0].current_status as string),
  );
  expect(statuses.filter((s) => s.startsWith("CNF"))).toEqual(["CNF/S1/1/LB"]);
  expect(statuses.filter((s) => s.startsWith("WL"))).toHaveLength(19);
  await user.dispose();
});

test("ST-12 hostile input is rejected safely", async ({ page, request }) => {
  const stations = await request.get("/api/v1/stations", { params: { q: "' OR 1=1 --" } });
  expect(stations.status()).toBe(200);
  expect(await stations.json()).toEqual([]);

  await register(page, "Test User");
  await page.goto(resultsUrl(DELHI, MUMBAI));
  await page.getByRole("button", { name: "Book SL on 22401" }).click();
  await fillPassenger(page, 0, { name: "<script>alert(1)</script>", age: 30, gender: "Male" });
  await page.getByRole("button", { name: "Continue to payment" }).click();
  await expect(page.getByText("2 to 50 letters; spaces, dots and apostrophes allowed.")).toBeVisible();
  await expect(page.getByRole("heading", { name: "Passenger details" })).toBeVisible();
});
