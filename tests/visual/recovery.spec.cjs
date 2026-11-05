const {test, expect} = require('playwright/test');
const fs = require('node:fs/promises');
const path = require('node:path');

test.use({actionTimeout:15000});

// Functional/layout checks run on every platform. Screenshots are review
// attachments, not comparisons against the existing Windows-only baselines.
const stories = [
  {id:'rivera', name:'Rivera', description:/Synthetic fictional accommodation arranged while/, days:[1,3,7]},
  {id:'bennett', name:'Bennett', description:/Synthetic fictional renter documentation with/, days:[1,3,7]},
  {id:'patel', name:'Patel', description:/Synthetic fictional sparse reports preserve/, days:[1,3,7]},
  {id:'chen', name:'Chen', description:/Synthetic fictional completed documentation remains/, days:[1,3,7,14,30]},
  {id:'johnson', name:'Johnson', description:/Synthetic fictional month of restored utilities/, days:[1,3,7,14,30]},
  {id:'lewis', name:'Lewis', description:/Synthetic fictional month ends in a new/, days:[1,3,7,14,30]},
];

async function settled(page) {
  await expect(page.getByTestId('stApp')).not.toHaveAttribute('data-test-script-state','running');
  await expect(page.getByTestId('stException')).toHaveCount(0);
}

async function select(page, label, option) {
  const input = page.getByRole('combobox', {name:label, exact:true});
  const current = await input.inputValue();
  if (typeof option === 'string' ? current === option : option.test(current)) return;
  // Recover if a popup closes while its control gains focus. Retry field
  // selection only; no load, status save, or approval operation is retried.
  await expect(async () => {
    if (await input.getAttribute('aria-expanded') !== 'true') {
      await input.locator('..').getByRole('button', {name:'Open', exact:true}).click({timeout:1500});
    }
    await page.getByRole('option', {name:option, exact:typeof option === 'string'}).click({timeout:1500});
    await expect(input).toHaveValue(option, {timeout:1500});
  }).toPass({timeout:15000, intervals:[100,250,500]});
  await settled(page);
}

async function recover(page) {
  const search = page.getByRole('combobox', {name:'Search menu', exact:true});
  await search.fill('open Recover');
  await expect(page.getByRole('option', {name:'Recover', exact:true})).toBeVisible();
  await search.press('Enter');
  await expect(page.getByText('Explore six fictional recovery journeys', {exact:true})).toBeVisible();
  await settled(page);
}

async function load(page, story, day) {
  const picker = page.getByRole('combobox', {name:'Fictional household', exact:true});
  if (!await picker.isVisible()) {
    await page.getByText('Explore six fictional recovery journeys', {exact:true}).click();
  }
  await select(page, 'Fictional household', new RegExp(`${story.name} household`));
  await expect(page.getByText(story.description)).toBeVisible();
  await select(page, 'Story checkpoint', `Day ${day}`);
  await page.getByRole('button', {name:'Load fictional checkpoint', exact:true}).click();
  await settled(page);
  await expect(page.getByRole('button', {name:'Leave fictional recovery scenario', exact:true})).toBeVisible();
  if (!(story.id === 'lewis' && day === 30)) {
    await expect(page.getByText(new RegExp(`SYNTHETIC DEMO.*${story.name} household.*Story as of October ${String(day + 1).padStart(2,'0')}, 2026`))).toBeVisible();
  }
}

async function layout(page, project) {
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth + 2)).toBeTruthy();
  const hero = page.locator('.rj-hero');
  const target = page.locator('.rj-target');
  const heroBox = await hero.boundingBox();
  const targetBox = await target.boundingBox();
  expect(heroBox.width).toBeGreaterThan(200);
  expect(targetBox.x).toBeGreaterThanOrEqual(heroBox.x);
  expect(targetBox.x + targetBox.width).toBeLessThanOrEqual(heroBox.x + heroBox.width + 2);
  const columns = await page.locator('.rj-changes').evaluate(el => getComputedStyle(el).gridTemplateColumns.split(' ').length);
  if (project === 'mobile') expect(columns).toBe(1);
  const call = page.getByRole('link', {name:'Call 911', exact:true});
  await expect(call).toBeVisible();
  await expect(call).toHaveAttribute('href','tel:911');
  // Inspect and focus the real call link, never activate a dial URI.
  await call.focus();
}

async function capture(page, info, name) {
  await settled(page);
  await page.getByTestId('stMain').evaluate(el => el.scrollTop = 0);
  if (name.startsWith('dashboard')) {
    const marker = name.includes('timeline') ? page.getByRole('heading', {name:'Your timeline', exact:true}) : page.locator('.rj-kicker').first();
    const bounds = await marker.boundingBox();
    const header = await page.locator('.st-key-top_toolbar').boundingBox();
    const emergency = await page.locator('.st-key-emergency_bar').boundingBox();
    await page.getByTestId('stMain').evaluate((el, offset) => el.scrollBy(0, offset), bounds.y - header.height - emergency.height - 24);
  }
  await page.mouse.move(0,0);
  await page.evaluate(() => document.fonts.ready);
  const directory = path.resolve('artifacts/recovery-review/screenshots');
  await fs.mkdir(directory, {recursive:true});
  const file = path.join(directory, `${info.project.name}-${name}.png`);
  await page.screenshot({path:file, fullPage:true, animations:'disabled', caret:'hide'});
  await info.attach(`${info.project.name}-${name}`, {path:file, contentType:'image/png'});
}

test.beforeEach(async ({page}) => {
  // The app and its WebSocket stay local; official links remain unvisited.
  await page.route('**/*', route => {
    const url = new URL(route.request().url());
    return ['127.0.0.1','localhost'].includes(url.hostname) ? route.continue() : route.abort();
  });
  await page.goto('/');
  await expect(page.getByRole('link', {name:'Call 911', exact:true})).toBeVisible();
  await recover(page);
});

test('all six fictional stories load every checkpoint with honest dates and a danger exit', async ({page}, info) => {
  test.setTimeout(150000);
  for (const story of stories) {
    for (const day of story.days) {
      await test.step(`${story.name} day ${day}`, async () => {
        await load(page, story, day);
        if (story.id === 'lewis' && day === 30) {
          await expect(page.getByText('Routine recovery actions are paused.', {exact:false})).toBeVisible();
          await expect(page.getByRole('heading', {name:'Your recovery, one step at a time.', exact:true})).toHaveCount(0);
          await expect(page.getByRole('button', {name:'Save progress', exact:true})).toHaveCount(0);
          await expect(page.getByRole('link', {name:'Call 911', exact:true})).toHaveAttribute('href','tel:911');
          await expect(page.getByRole('button', {name:"I Can't Call 911", exact:true})).toBeVisible();
          await capture(page, info, 'lewis-danger');
          await page.getByRole('button', {name:'Leave fictional recovery scenario', exact:true}).click();
          await settled(page);
          await expect(page.getByText('Explore six fictional recovery journeys', {exact:true})).toBeVisible();
          await page.getByText('Explore six fictional recovery journeys', {exact:true}).click();
          await expect(page.getByRole('button', {name:'Load fictional checkpoint', exact:true})).toBeVisible();
          return;
        }
        await expect(page.getByRole('heading', {name:'Your recovery, one step at a time.', exact:true})).toBeVisible();
        await expect(page.getByText(new RegExp(`SYNTHETIC DEMO.*${story.name} household.*Story as of October ${String(day + 1).padStart(2,'0')}, 2026`))).toBeVisible();
        await expect(page.locator('.rj-day')).toHaveText(String(day));
        await expect(page.getByRole('heading', {name:'Your timeline', exact:true})).toBeVisible();
        await expect(page.locator('.rj-timeline li')).not.toHaveCount(0);
        if (story.id === 'patel' && day === 3) {
          await expect(page.getByText('No new updates recorded.', {exact:false})).toBeVisible();
          await expect(page.locator('.rj-changes')).toHaveCount(0);
          await page.getByText('Your confirmed situation', {exact:true}).click();
          await expect(page.getByText('Children: Unknown', {exact:true})).toBeVisible();
          await expect(page.getByText('Adults: Unknown', {exact:true})).toBeVisible();
        }
        if (story.id === 'rivera' && day === 7) {
          await layout(page, info.project.name);
          await capture(page, info, 'dashboard-bright');
          await capture(page, info, 'dashboard-timeline-bright');
          await page.getByRole('button', {name:'Switch to dark mode', exact:true}).click();
          await expect(page.getByRole('button', {name:'Switch to bright mode', exact:true})).toBeVisible();
          await layout(page, info.project.name);
          await capture(page, info, 'dashboard-dark');
          await capture(page, info, 'dashboard-timeline-dark');
          await page.getByRole('button', {name:'Switch to bright mode', exact:true}).click();
        }
      });
    }
  }
});

test('Bennett pending revision needs a current safety recheck before approval', async ({page}, info) => {
  await load(page, stories[1], 7);
  await expect(page.getByText('Fictional update awaiting your review:', {exact:false})).toBeVisible();
  await expect(page.getByText('No new updates recorded.', {exact:false})).toBeVisible();
  await expect(page.getByRole('heading', {name:'Review reported transportation needs', exact:true})).toHaveCount(0);
  await page.getByText('Circumstances changed? Review an update', {exact:true}).click();
  await expect(page.getByText('Recheck current danger before approving this proposal.', {exact:true})).toBeVisible();
  await expect(page.getByRole('button', {name:'Approve this revision', exact:true})).toHaveCount(0);
  await select(page, 'Updated immediate danger assessment', 'No immediate danger reported');
  await expect(page.getByRole('button', {name:'Approve this revision', exact:true})).toBeVisible();
  await capture(page, info, 'bennett-pending-review');
  await page.getByRole('button', {name:'Approve this revision', exact:true}).click();
  await expect(page.getByText('Revision approved. Your earlier progress and plan history are preserved.', {exact:true})).toBeVisible();
  await expect(page.getByRole('heading', {name:'Review reported transportation needs', exact:true})).toBeVisible();
  await expect(page.getByText('Fictional update awaiting your review:', {exact:false})).toHaveCount(0);
  await page.getByText('Plan history and take-away copy', {exact:true}).click();
  await expect(page.getByText('2 approved plan version(s). Historical versions remain in SQLite.', {exact:true})).toBeVisible();
});

test('task filters and saved progress survive navigation and replay resume after refresh', async ({page}) => {
  await load(page, stories[0], 7);
  await select(page, 'Show tasks', 'Not started');
  const status = page.getByRole('combobox', {name:/^Status · /}).first();
  const taskLabel = await status.getAttribute('aria-label');
  expect(taskLabel).toBeTruthy();
  const form = page.getByTestId('stForm').filter({has:page.getByRole('combobox', {name:taskLabel, exact:true})});
  await select(page, taskLabel, 'In Progress');
  await form.getByRole('button', {name:'Save progress', exact:true}).click();
  await expect(page.getByText('Progress saved locally.', {exact:true})).toBeVisible();
  await select(page, 'Show tasks', 'In progress');
  await expect(page.getByRole('combobox', {name:taskLabel, exact:true})).toHaveValue('In Progress');
  const search = page.getByRole('combobox', {name:'Search menu', exact:true});
  await search.fill('open Household');
  await page.getByRole('option', {name:'Household', exact:true}).click();
  await expect(page.getByRole('button', {name:'Save household preferences', exact:true})).toBeVisible();
  await recover(page);
  await select(page, 'Show tasks', 'In progress');
  await expect(page.getByRole('combobox', {name:taskLabel, exact:true})).toHaveValue('In Progress');
  await page.getByText('User-reported task status history', {exact:true}).click();
  await expect(page.getByText(/NOT_STARTED -> IN_PROGRESS/)).toBeVisible();
  await page.getByText('Saved case · Keep this ID to resume', {exact:true}).click();
  const caseId = (await page.locator('code').filter({hasText:/^[0-9a-f]{8}-[0-9a-f-]{27}$/}).innerText()).trim();
  await page.reload();
  await recover(page);
  await page.getByText('Explore six fictional recovery journeys', {exact:true}).click();
  await page.getByRole('textbox', {name:'Replay case ID', exact:true}).fill(caseId);
  await page.getByRole('button', {name:'Resume fictional replay', exact:true}).click();
  await expect(page.getByRole('heading', {name:'Your recovery, one step at a time.', exact:true})).toBeVisible();
  await select(page, 'Show tasks', 'In progress');
  await expect(page.getByRole('combobox', {name:taskLabel, exact:true})).toHaveValue('In Progress');
  await page.getByText('Saved case · Keep this ID to resume', {exact:true}).click();
  await expect(page.locator('code').filter({hasText:caseId})).toHaveText(caseId);
});
