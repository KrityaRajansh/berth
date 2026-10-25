import { expect, test } from "@playwright/test";

import {
  ADMIN,
  DELHI,
  MUMBAI,
  TRAVEL_DATE,
  bookAndPay,
  evidence,
  login,
  register,
  resultsUrl,
  uniqueSuffix,
} from "./helpers";

test("ST-06 admin adds a station and a train that becomes bookable", async ({ page }) => {
  const suffix = uniqueSuffix();
  // Station codes are letters only: map the last three digits to A-J, e.g. "ZBCD".
  const letters = [...suffix.slice(-3)].map((d) => String.fromCharCode(65 + Number(d))).join("");
  const code = `Z${letters}`;
  const number = `4${suffix.slice(-4)}`;
  await login(page, ADMIN.email, ADMIN.password);

  await page.goto("/admin/stations");
  await page.getByLabel("Code").fill(code);
  await page.getByLabel("Name").fill("Berth Town");
  await page.getByLabel("City").fill("Berth Town");
  await page.getByRole("button", { name: "Add", exact: true }).click();
  await expect(page.getByRole("cell", { name: code, exact: true })).toBeVisible();

  await page.goto("/admin/trains");
  await page.getByLabel("Number").fill(number);
  await page.getByLabel("Name").fill("Course Project Link");
  await page.getByRole("button", { name: "Add and edit route" }).click();
  await expect(page.getByRole("heading", { name: `${number} Course Project Link` })).toBeVisible();

  await page.getByLabel("Stop 1 station code").fill("NDLS");
  await page.getByLabel("Stop 1 departure").fill("09:00");
  await page.getByLabel("Stop 1 distance").fill("0");
  await page.getByLabel("Stop 2 station code").fill(code);
  await page.getByLabel("Stop 2 arrival").fill("12:00");
  await page.getByLabel("Stop 2 distance").fill("180");
  await page.getByRole("button", { name: "Save route" }).click();
  await expect(page.getByText("Route saved.")).toBeVisible();

  await page.getByRole("button", { name: "Add coach" }).click();
  await page.getByLabel("Code", { exact: true }).last().fill("A1");
  await page.getByLabel("Class").last().selectOption("2A");
  await page.getByLabel("Berths").last().fill("48");
  await page.getByRole("button", { name: "Save coaches" }).click();
  await expect(page.getByText("Coaches saved.")).toBeVisible();
  await evidence(page, "st06-train-editor");

  await page.goto("/admin/runs");
  await page.getByLabel("Train (optional)").fill(number);
  await page.getByRole("button", { name: "Generate runs" }).click();
  await expect(page.getByText(/\d+ new runs created/)).toBeVisible();

  await page.goto(resultsUrl(DELHI, [code, "Berth Town"]));
  const train = page.getByRole("article").filter({ hasText: number });
  await expect(train).toContainText("Course Project Link");
  await expect(train).toContainText("Available 48");
  await evidence(page, "st06-new-train-in-search");
});

test("ST-07 admin sees booked passengers on the passenger chart", async ({ page }) => {
  await register(page, "Sana Qureshi");
  await page.goto(resultsUrl(DELHI, MUMBAI));
  await bookAndPay(page, "22401", "2A", [{ name: "Sana Qureshi", age: 27, gender: "Female" }]);
  await expect(page.getByRole("heading", { name: /^PNR \d{10}$/ })).toBeVisible();
  await page.getByRole("button", { name: "Log out" }).click();

  await login(page, ADMIN.email, ADMIN.password);
  await page.goto("/admin/runs");
  await page.getByLabel("Run date").fill(TRAVEL_DATE);
  await page.getByLabel("Train number").fill("22401");
  await page.getByRole("link", { name: "Chart" }).click();

  const row = page.getByRole("row").filter({ hasText: "Sana Qureshi" });
  await expect(row).toContainText("2A");
  await expect(row).toContainText(/A\d\/\d+/);
  await expect(row).toContainText("NDLS - MMCT");
  await evidence(page, "st07-passenger-chart");
});

test("admin can run a scheduled job from the jobs page", async ({ page }) => {
  await login(page, ADMIN.email, ADMIN.password);
  await page.goto("/admin/jobs");
  const card = page.getByRole("heading", { name: "payment-expiry" }).locator("xpath=../..");
  await card.getByRole("button", { name: "Run now" }).click();
  await expect(page.getByText(/payment-expiry: succeeded/)).toBeVisible();
  await expect(page.getByRole("cell", { name: "payment-expiry" }).first()).toBeVisible();
});
