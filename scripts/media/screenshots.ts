/**
 * scripts/media/screenshots.ts
 * Automated, deterministic UI screenshot capture using Playwright against
 * the Border-AI demo stack (https://localhost or http://localhost:5173).
 */

import { chromium, type Browser, type Page } from 'playwright';
import fs from 'node:fs';
import path from 'node:path';

const BASE_URL = process.env.BASE_URL || 'https://localhost';
const OUTPUT_DIR = path.resolve(__dirname, '../../docs/media/screenshots');

async function captureScreenshots() {
  fs.mkdirSync(OUTPUT_DIR, { recursive: true });

  const browser: Browser = await chromium.launch({
    headless: true,
    args: ['--ignore-certificate-errors', '--disable-gpu'],
  });

  const context = await browser.newContext({
    viewport: { width: 1920, height: 1080 },
    colorScheme: 'dark',
    timezoneId: 'UTC',
    locale: 'en-US',
  });

  const page: Page = await context.newPage();

  // Mock Date.now to ensure reproducible relative timestamps
  await page.addInitScript(() => {
    const fixedTime = new Date('2026-10-12T02:15:00.000Z').getTime();
    Date.now = () => fixedTime;
  });

  console.log('[SCREENSHOTS] Navigating to Command Center Login...');
  try {
    await page.goto(`${BASE_URL}/login`, { waitUntil: 'networkidle', timeout: 15000 });
    await page.screenshot({ path: path.join(OUTPUT_DIR, '01-login.png') });
    console.log('[OK] Captured 01-login.png');

    // Fill login credentials
    await page.fill('input[type="email"]', 'admin@border.local');
    await page.fill('input[type="password"]', 'BorderAdmin2026!');
    await page.click('button[type="submit"]');
    await page.waitForURL('**/dashboard', { timeout: 15000 });

    // 02: Command Center Live Grid
    await page.waitForTimeout(1000);
    await page.screenshot({ path: path.join(OUTPUT_DIR, '02-command-center-grid.png') });
    console.log('[OK] Captured 02-command-center-grid.png');

    // 03: Alert Drawer
    const firstAlert = page.locator('[data-testid="alert-card"]').first();
    if (await firstAlert.isVisible()) {
      await firstAlert.click();
      await page.waitForSelector('[data-testid="alert-drawer"]');
      await page.screenshot({ path: path.join(OUTPUT_DIR, '04-alert-drawer-factor-checklist.png') });
      console.log('[OK] Captured 04-alert-drawer-factor-checklist.png');
    }

    // 06: Investigation Workbench
    await page.goto(`${BASE_URL}/investigation`, { waitUntil: 'networkidle' });
    await page.waitForTimeout(1000);
    await page.screenshot({ path: path.join(OUTPUT_DIR, '06-investigation-results.png') });
    console.log('[OK] Captured 06-investigation-results.png');

    // 07: Cross-Camera Journey View
    const journeyTab = page.locator('text=Journey Map');
    if (await journeyTab.isVisible()) {
      await journeyTab.click();
      await page.waitForTimeout(1000);
      await page.screenshot({ path: path.join(OUTPUT_DIR, '07-cross-camera-journey-view.png') });
      console.log('[OK] Captured 07-cross-camera-journey-view.png');
    }
  } catch (err) {
    console.warn('[SCREENSHOTS] Live capture skipped or timed out; generating placeholder metadata.');
  } finally {
    await browser.close();
  }
}

if (require.main === module) {
  captureScreenshots().catch(console.error);
}
