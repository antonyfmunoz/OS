import puppeteer from 'puppeteer-core';

const CHROMIUM_PATH = '/nix/store/zi4f80l169xlmivz8vja8wlphq74qqk0-chromium-125.0.6422.141/bin/chromium';
const BASE_URL = 'http://localhost:5000';
const OUTPUT_DIR = '/home/runner/workspace/client/public/images';

const HIDE_TUTORIAL_CSS = `
  div[style*="z-index: 10000"], 
  div[style*="z-index:10000"] { 
    display: none !important; 
  }
`;

const PAGES = [
  { url: '/dashboard', name: 'preview-dashboard', wait: 3000 },
  { url: '/missions', name: 'preview-mission-flow', wait: 3000 },
  { url: '/ai', name: 'preview-nova-chat', wait: 3000 },
  { url: '/profile', name: 'preview-profile-stats', wait: 3000 },
];

async function hideTutorials(page: any) {
  await page.addStyleTag({ content: HIDE_TUTORIAL_CSS });
  await page.evaluate(() => {
    document.querySelectorAll('div').forEach(el => {
      const style = el.getAttribute('style') || '';
      if (style.includes('10000')) {
        (el as HTMLElement).style.display = 'none';
      }
    });
  });
  await new Promise(r => setTimeout(r, 300));
}

async function loginOnPage(page: any) {
  await page.goto(`${BASE_URL}/login?access=beta`, { waitUntil: 'load', timeout: 60000 });
  await new Promise(r => setTimeout(r, 2000));
  await page.evaluate(() => { localStorage.setItem('lyfeos_access', 'true'); });
  await page.goto(`${BASE_URL}/login`, { waitUntil: 'load', timeout: 60000 });
  await new Promise(r => setTimeout(r, 2000));

  console.log('Logging in...');
  await page.type('input#identifier', 'alex.chen@demo.lyfeos.com');
  await page.type('input#password', 'demo123456');
  await page.click('button[type="submit"]');
  await new Promise(r => setTimeout(r, 5000));

  let attempts = 0;
  while (attempts < 5) {
    await page.goto(`${BASE_URL}/dashboard`, { waitUntil: 'load', timeout: 30000 });
    await new Promise(r => setTimeout(r, 2000));
    if (!page.url().includes('/login') && !page.url().includes('/waitlist') && !page.url().includes('/ceremony')) {
      break;
    }
    attempts++;
    console.log(`Auth not ready (attempt ${attempts}), at: ${page.url()}, retrying...`);
    await new Promise(r => setTimeout(r, 1500));
  }
  console.log('Logged in, at:', page.url());

  await page.evaluate(() => {
    return fetch('/api/profile', {
      method: 'PATCH',
      headers: { 'Content-Type': 'application/json' },
      credentials: 'include',
      body: JSON.stringify({ completedTutorials: ['dashboard', 'missions', 'profile', 'chronilog', 'ai'] }),
    });
  });
}

async function captureAffirmation(page: any, suffix: string) {
  console.log('Scrolling to affirmation section (same /profile page)...');

  await page.evaluate(() => {
    const el = document.querySelector("[data-tour='profile-widget-player-affirmation']");
    if (el) {
      el.scrollIntoView({ block: 'start', behavior: 'instant' });
      return;
    }
    const all = Array.from(document.querySelectorAll('h3, h4, span, div, p'));
    for (const h of all) {
      if (h.textContent?.toLowerCase().includes('affirmation') && h.textContent.length < 50) {
        (h as HTMLElement).scrollIntoView({ block: 'start', behavior: 'instant' });
        return;
      }
    }
    window.scrollTo(0, document.body.scrollHeight * 0.6);
  });
  await new Promise(r => setTimeout(r, 1000));

  const name = `preview-affirmation${suffix}`;
  await page.screenshot({ path: `${OUTPUT_DIR}/${name}.png`, fullPage: false });
  console.log(`Saved ${name}.png`);
}

async function captureOnboarding(page: any, suffix: string) {
  console.log('Resetting onboarding status for demo user...');
  await page.evaluate(() => {
    return fetch('/api/profile', {
      method: 'PATCH',
      headers: { 'Content-Type': 'application/json' },
      credentials: 'include',
      body: JSON.stringify({ onboardingCompleted: false, completedOnboardingMissions: [] }),
    });
  });
  await new Promise(r => setTimeout(r, 1000));

  console.log('Navigating to /onboarding via SPA pushState...');
  await page.evaluate(() => {
    window.history.pushState({}, '', '/onboarding');
    window.dispatchEvent(new PopStateEvent('popstate'));
  });
  await new Promise(r => setTimeout(r, 5000));

  try {
    await page.waitForFunction(
      () => {
        const body = document.body.innerText || '';
        return !body.includes('Loading...') && (
          body.includes('Start') || body.includes('Mission') || body.includes('Know') ||
          body.includes('username') || body.includes('LYFEOS') && body.length > 200
        );
      },
      { timeout: 20000 }
    );
  } catch {
    console.log('  Onboarding content did not fully load, capturing anyway...');
  }
  await new Promise(r => setTimeout(r, 2000));

  await hideTutorials(page);
  const name = `preview-onboarding${suffix}`;
  await page.screenshot({ path: `${OUTPUT_DIR}/${name}.png`, fullPage: false });
  console.log(`Saved ${name}.png (at: ${page.url()})`);

  console.log('Restoring onboarding status for demo user...');
  await page.evaluate(() => {
    return fetch('/api/profile', {
      method: 'PATCH',
      headers: { 'Content-Type': 'application/json' },
      credentials: 'include',
      body: JSON.stringify({ onboardingCompleted: true, completedOnboardingMissions: [0,1,2,3,4,5,6,7] }),
    });
  });
  await new Promise(r => setTimeout(r, 500));

  console.log('Navigating back to /dashboard...');
  await page.evaluate(() => {
    window.history.pushState({}, '', '/dashboard');
    window.dispatchEvent(new PopStateEvent('popstate'));
  });
  await new Promise(r => setTimeout(r, 2000));
}

async function captureSet(page: any, suffix: string) {
  for (const p of PAGES) {
    console.log(`Navigating to ${p.url}...`);
    await page.goto(`${BASE_URL}${p.url}`, { waitUntil: 'load', timeout: 60000 });
    await new Promise(r => setTimeout(r, p.wait));

    const url = page.url();
    if (url.includes('/login') || url.includes('/waitlist')) {
      console.log(`  WARNING: redirected to ${url}`);
    }

    await hideTutorials(page);
    await page.screenshot({ path: `${OUTPUT_DIR}/${p.name}${suffix}.png`, fullPage: false });
    console.log(`Saved ${p.name}${suffix}.png (at: ${page.url()})`);

    if (p.name === 'preview-profile-stats') {
      await captureAffirmation(page, suffix);
    }
  }

  await captureOnboarding(page, suffix);
}

async function captureScreenshots() {
  const browser = await puppeteer.launch({
    executablePath: CHROMIUM_PATH,
    headless: 'shell',
    args: ['--no-sandbox', '--disable-setuid-sandbox', '--disable-gpu', '--disable-dev-shm-usage', '--disable-web-security'],
  });

  console.log('=== Desktop screenshots (1280x800) ===');
  const desktopPage = await browser.newPage();
  await desktopPage.setViewport({ width: 1280, height: 800, deviceScaleFactor: 2 });
  await loginOnPage(desktopPage);
  await captureSet(desktopPage, '');
  await desktopPage.close();

  console.log('\n=== Mobile screenshots (390x844) ===');
  const mobilePage = await browser.newPage();
  await mobilePage.setViewport({ width: 390, height: 844, deviceScaleFactor: 2 });
  await loginOnPage(mobilePage);
  await captureSet(mobilePage, '-mobile');
  await mobilePage.close();

  await browser.close();
  console.log('\nAll screenshots captured!');
}

captureScreenshots().catch(console.error);
