/**
 * Acceptance scenarios AT-01 to AT-08 from the test plan, written from the point of
 * view of each user class (SRS 4.3). Each test ends with the acceptance criterion.
 */
import { expect, test } from "@playwright/test";

import {
  ADMIN,
  DELHI,
  MUMBAI,
  TRAVEL_DATE,
  adminApi,
  bookAndPay,
  createSmallTrain,
  evidence,
  istDate,
  login,
  register,
  resultsUrl,
} from "./helpers";

const BASE = process.env.E2E_BASE_URL ?? "http://localhost:5173";

test("AT-01 a new visitor plans a trip, compares classes and registers", async ({ page }) => {
  await page.goto(resultsUrl(DELHI, MUMBAI));
  const train = page.getByRole("article").filter({ hasText: "22401" });
  for (const cls of ["SL", "3A", "2A", "1A"]) {
    await expect(train.getByRole("button", { name: `Book ${cls} on 22401` })).toBeVisible();
  }
  await expect(train).toContainText("₹643"); // SL fare for 1384 km
  await evidence(page, "at01-compare-classes");

  await register(page, "Farah Ali");
  await expect(page.getByRole("link", { name: "Farah" })).toBeVisible();
});

test("AT-02 a passenger books for a family of four and gets the e-ticket", async ({ page }) => {
  await register(page, "Vivek Menon");
  await page.goto(resultsUrl(DELHI, MUMBAI));
  await bookAndPay(page, "22401", "3A", [
    { name: "Vivek Menon", age: 42, gender: "Male" },
    { name: "Latha Menon", age: 39, gender: "Female" },
    { name: "Anu Menon", age: 12, gender: "Female" },
    { name: "Ravi Menon", age: 9, gender: "Male" },
  ]);
  await expect(page.getByRole("heading", { name: /^PNR \d{10}$/ })).toBeVisible();
  for (const name of ["Vivek Menon", "Latha Menon", "Anu Menon", "Ravi Menon"]) {
    await expect(page.getByRole("row").filter({ hasText: name })).toContainText("CNF");
  }
  await evidence(page, "at02-family-booking");
  const download = page.waitForEvent("download");
  await page.getByRole("link", { name: "Download e-ticket (PDF)" }).click();
  expect((await download).suggestedFilename()).toMatch(/\.pdf$/);
});

test("AT-03 a waitlisted passenger is confirmed when someone cancels", async ({ browser }) => {
  const admin = await adminApi(BASE);
  const train = await createSmallTrain(admin, 1);
  const url = resultsUrl(DELHI, train.station);

  const first = await browser.newPage();
  await register(first, "Isha Verma");
  await first.goto(url);
  await bookAndPay(first, train.number, "SL", [{ name: "Isha Verma", age: 30, gender: "Female" }]);
  await expect(first.getByRole("heading", { name: /^PNR / })).toBeVisible();

  const second = await browser.newPage();
  await register(second, "Omar Siddiqui");
  await second.goto(url);
  await expect(second.getByRole("article")).toContainText("WL 1");
  await bookAndPay(second, train.number, "SL", [{ name: "Omar Siddiqui", age: 33, gender: "Male" }]);
  const waitlisted = second.getByRole("row").filter({ hasText: "Omar Siddiqui" });
  await expect(waitlisted).toContainText("WL 1");
  await evidence(second, "at03-waitlisted");

  await first.getByLabel("Select Isha Verma for cancellation").check();
  await first.getByRole("button", { name: "Check refund for 1 passenger" }).click();
  await first.getByRole("button", { name: "Confirm cancellation" }).click();
  await expect(first.getByRole("row").filter({ hasText: "Isha Verma" })).toContainText("Cancelled");

  await second.reload();
  await expect(second.getByRole("row").filter({ hasText: "Omar Siddiqui" })).toContainText(
    "CNF/S1/1",
  );
  await evidence(second, "at03-promoted");
  await admin.dispose();
});

test("AT-04 cancelling one traveller shows the refund before confirming", async ({ page }) => {
  await register(page, "Tara Singh");
  // Five days ahead keeps departure more than 48 hours away: fare minus the flat fee.
  await page.goto(resultsUrl(DELHI, MUMBAI, istDate(5)));
  await bookAndPay(page, "22401", "SL", [
    { name: "Tara Singh", age: 50, gender: "Female" },
    { name: "Jas Singh", age: 52, gender: "Male" },
  ]);
  await page.getByLabel("Select Jas Singh for cancellation").check();
  await page.getByRole("button", { name: "Check refund for 1 passenger" }).click();

  // SL fare Rs 643 minus the Rs 120 Sleeper cancellation fee (BR-06).
  await expect(page.getByText("Refund: ₹523")).toBeVisible();
  await evidence(page, "at04-refund-quote");
  await page.getByRole("button", { name: "Confirm cancellation" }).click();
  await expect(page.getByRole("row").filter({ hasText: "Jas Singh" })).toContainText("₹523");
});

test("AT-05 a relative checks a PNR without an account", async ({ page, browser }) => {
  await register(page, "Kiran Rao");
  await page.goto(resultsUrl(DELHI, MUMBAI));
  await bookAndPay(page, "22401", "2A", [{ name: "Kiran Rao", age: 61, gender: "Male" }]);
  const pnr = (await page.getByRole("heading", { name: /^PNR / }).textContent())!.slice(4);

  const relative = await browser.newPage();
  await relative.goto(`/pnr/${pnr}`);
  await expect(relative.getByRole("link", { name: "Log in" })).toBeVisible(); // not logged in
  await expect(relative.getByRole("cell", { name: "Ki*** Ra*" })).toBeVisible();
  await expect(relative.getByText("Booked").first()).toBeVisible();
  await evidence(relative, "at05-pnr-status");
});

test("AT-06 the administrator adds a train and opens it for booking", async ({ page }) => {
  const admin = await adminApi(BASE);
  const train = await createSmallTrain(admin, 72);
  await admin.dispose();

  await login(page, ADMIN.email, ADMIN.password);
  await page.goto(`/admin/trains/${train.number}`);
  await expect(page.getByLabel("Stop 2 station code")).toHaveValue(train.station[0]);
  await page.goto(resultsUrl(DELHI, train.station));
  await expect(page.getByRole("article").filter({ hasText: train.number })).toContainText(
    "Available 72",
  );
  await evidence(page, "at06-new-train-bookable");
});

test("AT-07 the administrator checks who is travelling on a run", async ({ page }) => {
  await register(page, "Neha Joshi");
  await page.goto(resultsUrl(DELHI, MUMBAI));
  await bookAndPay(page, "22401", "1A", [{ name: "Neha Joshi", age: 36, gender: "Female" }]);
  await expect(page.getByRole("heading", { name: /^PNR / })).toBeVisible();
  await page.getByRole("button", { name: "Log out" }).click();

  await login(page, ADMIN.email, ADMIN.password);
  await page.goto("/admin/runs");
  await page.getByLabel("Run date").fill(TRAVEL_DATE);
  await page.getByLabel("Train number").fill("22401");
  await page.getByRole("link", { name: "Chart" }).click();
  await expect(page.getByRole("row").filter({ hasText: "Neha Joshi" })).toContainText(/H1\/\d+/);
});

test("AT-08 cancelling a train run refunds every passenger in full", async ({ page, browser }) => {
  const admin = await adminApi(BASE);
  const train = await createSmallTrain(admin, 2);
  await admin.dispose();

  const traveller = await browser.newPage();
  await register(traveller, "Arjun Nair");
  await traveller.goto(resultsUrl(DELHI, train.station));
  await bookAndPay(traveller, train.number, "SL", [
    { name: "Arjun Nair", age: 28, gender: "Male" },
    { name: "Divya Nair", age: 27, gender: "Female" },
    { name: "Mohan Nair", age: 60, gender: "Male" },
  ]);
  await expect(traveller.getByRole("row").filter({ hasText: "Mohan Nair" })).toContainText("WL 1");

  await login(page, ADMIN.email, ADMIN.password);
  await page.goto("/admin/runs");
  await page.getByLabel("Run date").fill(TRAVEL_DATE);
  await page.getByLabel("Train number").fill(train.number);
  await page.getByRole("button", { name: "Cancel run" }).click();
  await page.getByRole("button", { name: "Cancel run and refund all" }).click();
  await expect(page.getByText("Cancelled", { exact: true })).toBeVisible();

  await traveller.reload();
  await expect(traveller.getByText("Cancelled").first()).toBeVisible();
  await expect(traveller.getByText("Refunded")).toBeVisible();
  for (const name of ["Arjun Nair", "Divya Nair", "Mohan Nair"]) {
    await expect(traveller.getByRole("row").filter({ hasText: name })).toContainText("₹");
  }
  await evidence(traveller, "at08-run-cancelled");
});
