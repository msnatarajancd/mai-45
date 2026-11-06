const {test, expect} = require('playwright/test');

async function openProgress(page) {
  await page.goto('/');
  const search = page.getByRole('combobox', {name:'Search menu', exact:true});
  await search.fill('recovery progress');
  await page.getByRole('option', {name:'Recovery Progress', exact:true}).click();
  await expect(page.getByRole('heading', {name:'Your recovery, coming into view.', exact:true})).toBeVisible();
}

async function refresh(page) {
  await page.getByRole('button', {name:'Refresh checks', exact:true}).click();
  // A collapsed last-run expander may retain its hidden strip during rerenders.
  await expect(page.locator('.rp-run-strip:visible')).toBeVisible();
  await expect(page.locator('.rp-journey')).toBeVisible({timeout:30000});
  await expect(page.getByRole('button', {name:'Refresh checks', exact:true})).toBeEnabled({timeout:30000});
}

test('manual refresh, transparent details, stale checkpoint, responsive themes', async ({page}, info) => {
  await openProgress(page);
  await expect(page.getByRole('link', {name:'Call 911', exact:true})).toBeVisible();
  await expect(page.locator('.rp-source-badge')).toHaveText('SYNTHETIC STORY');
  await refresh(page);
  await expect(page.locator('.rp-card')).toHaveCount(4);
  await expect(page.getByRole('heading', {name:'Home & daily life', exact:true})).toBeVisible();
  await expect(page.getByRole('heading', {name:'Costs & funding', exact:true})).toBeVisible();
  await expect(page.locator('.rp-next-action')).toHaveCount(1);
  if (info.project.name === 'desktop') {
    await expect(page.locator('.rp-next-action')).toBeInViewport({ratio:1});
    await expect(page.getByRole('button', {name:'Open next step →', exact:true})).toBeInViewport();
  }
  await page.getByText('Timing & assumptions', {exact:true}).click();
  await expect(page.getByText('Illustrative synthetic ranges', {exact:true})).toBeVisible();
  await page.getByText('View details · Temporary housing', {exact:true}).click();
  await expect(page.getByText('Housing category', {exact:true})).toBeVisible();
  await expect(page.getByText(/Source: synthetic/).first()).toBeVisible();
  await page.getByText('View details · Temporary housing', {exact:true}).click();
  await expect(page.getByText('Housing category', {exact:true})).toBeHidden();
  await expect(page.getByTestId('stApp')).not.toHaveAttribute('data-test-script-state','running');
  await page.getByTestId('stMain').evaluate(el => el.scrollTop = 0);
  // Every visible state is named; reduced motion does not hide lifecycle text.
  expect(await page.locator('.rp-card .rp-signal').allTextContents()).toHaveLength(4);
  expect(await page.evaluate(()=>document.documentElement.scrollWidth > window.innerWidth)).toBe(false);
  await page.mouse.move(0,0);
  await page.screenshot({path:`artifacts/recovery-progress-${info.project.name}-bright.png`, fullPage:true});
  if (info.project.name === 'desktop') {
    await page.locator('.rp-next-action').screenshot({path:'artifacts/recovery-progress-desktop-next-action.png'});
    await page.getByTestId('stMain').evaluate(main => {
      const title = document.querySelector('.rp-section-title');
      main.scrollTop += title.getBoundingClientRect().top - 210;
    });
    await page.screenshot({path:'artifacts/recovery-progress-desktop-cards-bright.png', fullPage:true});
  }
  await page.getByRole('button', {name:'Switch to dark mode', exact:true}).click();
  await expect(page.locator('.rp-journey')).toBeVisible();
  await expect(page.getByTestId('stApp')).not.toHaveAttribute('data-test-script-state','running');
  await page.getByTestId('stMain').evaluate(el => el.scrollTop = 0);
  await page.mouse.move(0,0);
  await page.screenshot({path:`artifacts/recovery-progress-${info.project.name}-dark.png`, fullPage:true});
  await page.getByText('Choose story or saved case', {exact:true}).click();
  const checkpoint = page.getByRole('combobox', {name:'Story checkpoint', exact:true});
  await expect(async () => {
    if (await checkpoint.getAttribute('aria-expanded') !== 'true') {
      await checkpoint.locator('..').getByRole('button', {name:'Open', exact:true}).click({timeout:1500});
    }
    await page.getByRole('option', {name:'2 · An update', exact:true}).click({timeout:1500});
    await expect(checkpoint).toHaveValue('2 · An update', {timeout:1500});
  }).toPass({timeout:10000, intervals:[100,250,500]});
  await expect(page.getByText(/Outdated results — refresh checks/)).toBeVisible();
  await expect(page.locator('.rp-next-action')).toHaveCount(0);
  await expect(page.getByRole('button', {name:'Refresh checks', exact:true})).toBeEnabled();
});

test('no saved case has an honest empty state and no synthetic substitution', async ({page}) => {
  await openProgress(page);
  await page.getByText('Choose story or saved case', {exact:true}).click();
  await page.getByText('Saved recovery case', {exact:true}).click();
  await expect(page.getByText(/No synthetic results are substituted/)).toBeVisible();
  await expect(page.getByRole('button', {name:'Refresh checks', exact:true})).toHaveCount(0);
});

async function chooseDemoOption(page, field, label) {
  const input = page.getByRole('combobox', {name:field, exact:true});
  await expect(async () => {
    if (await input.getAttribute('aria-expanded') !== 'true') {
      await input.locator('..').getByRole('button', {name:'Open', exact:true}).click({timeout:1500});
    }
    await page.getByRole('option', {name:label, exact:true}).click({timeout:1500});
    await expect(input).toHaveValue(label, {timeout:1500});
  }).toPass({timeout:10000, intervals:[100,250,500]});
}

test('expanded large-household story shows whole-household capacity', async ({page}) => {
  await openProgress(page);
  await page.getByText('Choose story or saved case', {exact:true}).click();
  await chooseDemoOption(page, 'Household story', 'Santos household');
  await chooseDemoOption(page, 'Story checkpoint', '2 · An update');
  await page.getByText('Choose story or saved case', {exact:true}).click();
  await expect(page.locator('.rp-context')).toContainText('8 people');
  await refresh(page);
  await expect(page.locator('.rp-card').filter({hasText:'Temporary housing'})).toContainText('2 rooms needed');
  await expect(page.locator('.rp-next-action')).toContainText('Confirm a suitable place to stay');
});

test('expanded failure story stays unknown and new danger pauses checks', async ({page}) => {
  await openProgress(page);
  await page.getByText('Choose story or saved case', {exact:true}).click();
  await chooseDemoOption(page, 'Household story', 'Campbell household');
  await chooseDemoOption(page, 'Story checkpoint', '2 · An update');
  await page.getByText('Choose story or saved case', {exact:true}).click();
  await refresh(page);
  const utility = page.locator('.rp-card').filter({hasText:'Utility health checker'});
  await expect(utility).toContainText("Couldn't update");
  await expect(utility).toHaveClass(/rp-state-unknown/);
  await page.getByText('Choose story or saved case', {exact:true}).click();
  await chooseDemoOption(page, 'Household story', 'Fernandez household');
  await chooseDemoOption(page, 'Story checkpoint', '2 · An update');
  await expect(page.getByText(/Routine checks are paused/)).toBeVisible();
  await expect(page.getByRole('button', {name:'Refresh checks', exact:true})).toBeDisabled();
  await expect(page.getByRole('link', {name:'Call 911', exact:true})).toBeVisible();
  await expect(page.locator('.rp-next-action')).toHaveCount(0);
});
