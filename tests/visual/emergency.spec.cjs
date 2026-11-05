const {test, expect} = require('playwright/test');

test.beforeEach(async ({page}) => {
  await page.goto('/');
  await expect(page.getByRole('link', {name:'Call 911', exact:true})).toBeVisible();
});

async function openHelp(page) {
  await page.getByRole('button', {name:'I Need Help Now', exact:true}).click();
  await expect(page.getByRole('heading', {name:'I Need Help Now', exact:true})).toBeVisible();
}

async function county(page) {
  await page.getByRole('combobox', {name:'Where is help needed?'}).click();
  await page.getByRole('option', {name:'Miami-Dade County, Florida', exact:true}).click();
}

test('contact actions are ordered, usable, and do not initiate a call automatically', async ({page}, info) => {
  const call = page.getByRole('link', {name:'Call 911', exact:true});
  const cannot = page.getByRole('button', {name:"I Can't Call 911", exact:true});
  await expect(call).toHaveCount(1);
  await expect(cannot).toHaveCount(1);
  await expect(call).toHaveAttribute('href','tel:911');
  expect(await call.evaluate(el => !!(el.compareDocumentPosition(
    [...document.querySelectorAll('button')].find(b=>b.innerText === "I Can't Call 911")) & Node.DOCUMENT_POSITION_FOLLOWING))).toBeTruthy();
  expect((await call.boundingBox()).height).toBeGreaterThanOrEqual(44);
  expect((await cannot.boundingBox()).height).toBeGreaterThanOrEqual(44);
  await call.focus();
  await expect(call).toBeFocused();
  await page.keyboard.press('Tab');
  await expect(cannot).toBeFocused();
  // Never click the real tel URI in automated or simulated demonstrations.
  await openHelp(page);
  await expect(page.getByRole('link', {name:'Call 911', exact:true})).toHaveCount(1);
  await page.screenshot({path:`artifacts/emergency-${info.project.name}.png`,fullPage:true});
});

test('future transport uses official planning links with unknown availability', async ({page}) => {
  await openHelp(page);
  await county(page);
  await page.getByRole('textbox', {name:'Describe the situation (optional)'}).fill(
    'We may need accessible evacuation transport next week');
  await page.getByRole('button', {name:'Show assistance options', exact:true}).click();
  await expect(page.getByRole('link', {name:'Check EEAP registration timing'})).toBeVisible();
  await expect(page.getByText(/No pickup, enrollment, or response is guaranteed/)).toBeVisible();
  await expect(page.getByText('Emergency access comes first.',{exact:false})).toHaveCount(0);
  await expect(page.getByRole('link', {name:'Call 911', exact:true})).toBeVisible();
});

test('current danger interrupts without an AI turn and retains both exits', async ({page}) => {
  await openHelp(page);
  await page.getByRole('textbox', {name:'Describe the situation (optional)'}).fill(
    'My father is trapped and water is rising');
  await page.getByRole('button', {name:'Show assistance options', exact:true}).click();
  await expect(page.getByText('Routine recovery actions are paused.',{exact:false})).toBeVisible();
  await expect(page.getByRole('textbox', {name:'Describe the situation (optional)'})).toHaveCount(0);
  await expect(page.getByRole('button', {name:'Generate cited explanation'})).toHaveCount(0);
  await expect(page.getByRole('link', {name:'Call 911', exact:true})).toHaveCount(1);
  await page.getByRole('button', {name:"I Can't Call 911", exact:true}).click();
  await expect(page.getByText('ReadyRelief cannot send a text',{exact:false})).toBeVisible();
  await expect(page.getByRole('button', {name:'Return to app — this does not confirm safety'})).toBeVisible();
});

test('cannot-call information respects incident area and does not offer connectivity repair', async ({page}) => {
  await page.getByRole('button', {name:"I Can't Call 911", exact:true}).click();
  await expect(page.getByRole('link', {name:'Miami-Dade Text-to-911 information'})).toHaveCount(0);
  await county(page);
  await expect(page.getByRole('link', {name:'Miami-Dade Text-to-911 information'})).toBeVisible();
  await page.getByText('No usable connection',{exact:true}).click();
  await expect(page.getByText('ReadyRelief cannot restore cellular service',{exact:false})).toBeVisible();
  await expect(page.locator('a[href^="sms:"]')).toHaveCount(0);
  await page.getByRole('button', {name:"I Can't Call 911", exact:true}).click();
  await expect(page.getByRole('heading', {name:"If you can't call 911"})).toBeVisible();
});

test('emergency actions remain reachable while scrolling and at enlarged text', async ({page}) => {
  await openHelp(page);
  await page.getByRole('button', {name:'Next · Review recovery needs'}).scrollIntoViewIfNeeded();
  const call = page.getByRole('link', {name:'Call 911', exact:true});
  const viewport = page.viewportSize();
  let bounds = await call.boundingBox();
  const header = await page.locator('.st-key-top_toolbar').boundingBox();
  const bar = await page.locator('.st-key-emergency_bar').boundingBox();
  expect(bar.y).toBeGreaterThanOrEqual(header.y + header.height);
  expect(bounds.y).toBeGreaterThanOrEqual(0);
  expect(bounds.y + bounds.height).toBeLessThanOrEqual(viewport.height);
  await page.addStyleTag({content:'html {font-size:200% !important;}'});
  await call.scrollIntoViewIfNeeded();
  await expect(call).toBeVisible();
  const overflow = await page.evaluate(() => document.documentElement.scrollWidth > window.innerWidth + 2);
  expect(overflow).toBeFalsy();
});


test('Recovery primary action and emergency access remain clear through overlays', async ({page}) => {
  await page.getByRole('button', {name:'Start my recovery',exact:true}).click();
  await expect(page.getByRole('button',{name:'Continue to Review',exact:true})).toBeVisible();
  await page.getByTestId('stMain').evaluate(e=>e.scrollTop=0);
  await expect(page.getByRole('button',{name:'Continue to Review',exact:true})).toBeInViewport();
  await expect(page.getByRole('button',{name:'Find Help Now',exact:true})).toBeVisible();
  await expect(page.getByRole('button',{name:'Resume My Recovery',exact:true})).toBeVisible();
  const check = async () => {
    for (const control of [page.getByRole('link',{name:'Call 911',exact:true}),page.getByRole('button',{name:"I Can't Call 911",exact:true})]) {
      await expect(control).toBeInViewport();
      expect(await control.evaluate(el=>{const r=el.getBoundingClientRect();return el.contains(document.elementFromPoint(r.x+r.width/2,r.y+r.height/2));})).toBeTruthy();
    }
  };
  await page.getByTestId('stMain').evaluate(e=>e.scrollTop=e.scrollHeight);
  await check();
  await page.getByRole('button',{name:'Ask ReadyRelief',exact:true}).click();
  await check();
  await page.getByRole('button',{name:'Close chat',exact:true}).click();
  await page.getByRole('button',{name:'Start walkthrough',exact:true}).click();
  await check();
  const welcome=await page.locator('.st-key-tour_welcome').boundingBox();
  const bar=await page.locator('.st-key-emergency_bar').boundingBox();
  expect(welcome.y).toBeGreaterThanOrEqual(bar.y+bar.height);
});
