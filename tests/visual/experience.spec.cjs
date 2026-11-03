const {test,expect}=require('playwright/test');
async function ready(page){
 await page.goto('/');
 await expect(page.getByRole('button',{name:'Start my recovery',exact:true})).toBeVisible();
 await expect(page.getByTestId('stApp')).not.toHaveAttribute('data-test-script-state','running');
 await page.evaluate(()=>document.fonts.ready);
}
async function screen(page,name){
 await page.mouse.move(0,0);
 await expect(page.getByTestId('stApp')).not.toHaveAttribute('data-test-script-state','running');
 await expect(page).toHaveScreenshot(name,{caret:'hide'});
}
test('readable home, themes, search and persistent navigation',async({page},info)=>{
 await ready(page);
 const desktop=info.project.name!=='mobile';
 const original=page.viewportSize();
 if(desktop){
  await expect(page.locator('.st-key-nav_Protect button')).toBeInViewport();
  // Reproduce Streamlit's retained collapsed state, including resize back to desktop.
  await page.getByTestId('stSidebarCollapseButton').locator('button').evaluate(e=>e.click());
  await expect(page.locator('.st-key-nav_Protect button')).toBeInViewport();
  await page.setViewportSize({width:390,height:844});
  await expect(page.getByRole('button',{name:'Navigate',exact:true})).toBeVisible();
  await page.setViewportSize(original);
  await expect(page.locator('.st-key-nav_Protect button')).toBeInViewport();
 }
 if(desktop){
  const before=await page.locator('.block-container').boundingBox();
  await page.locator('.st-key-sidebar_toggle').getByRole('button',{name:'Hide navigation',exact:true}).click();
  await expect(page.getByTestId('stSidebar')).toBeHidden();
  expect((await page.locator('.block-container').boundingBox()).width).toBeGreaterThan(before.width);
  await screen(page,'home-collapsed.png');
  await page.locator('.st-key-toolbar_toggle').getByRole('button',{name:'Show navigation',exact:true}).click();
  await expect(page.locator('.st-key-nav_Protect button')).toBeInViewport();
 }
 await screen(page,'home-bright.png');
 const tiny=await page.locator('.rr-badge,.rr-visual-heading,.rr-card-top>span,.rr-trustline,.rr-visual-foot').evaluateAll(es=>es.filter(e=>parseFloat(getComputedStyle(e).fontSize)<12).length);
 expect(tiny).toBe(0);
 await page.getByRole('button',{name:'Switch to dark mode',exact:true}).click();
 await expect(page.getByRole('button',{name:'Switch to bright mode',exact:true})).toBeVisible();
 await screen(page,'home-dark.png');
 const input=page.getByRole('combobox',{name:'Search menu',exact:true});
 await input.fill('weather');
 await expect(page.getByRole('option',{name:'Protect',exact:true})).toBeVisible();
 await screen(page,'search-dark.png');
 await input.press('Enter');
 await expect(page.getByRole('button',{name:'Show simulated alert',exact:true})).toBeVisible();
 if(desktop)await expect(page.locator('.st-key-nav_Household button')).toBeInViewport();
 else{
  await page.getByRole('button',{name:'Navigate',exact:true}).click();
  await expect(page.getByTestId('stPopoverBody').getByRole('button',{name:'Household',exact:true})).toBeVisible();
 }
});
test('tour locates every control and cleans up',async({page})=>{
 await ready(page);
 await page.getByRole('button',{name:'Start walkthrough',exact:true}).click();
 const spotlight=page.getByTestId('rr-tour-spotlight');
 for(let step=1;step<=6;step++){
  await expect(page.locator('.st-key-guided_tour')).toContainText(`STEP ${step} OF 6`);
  await expect(spotlight).toBeVisible();
  if(step===3)await page.getByTestId('stMain').evaluate(e=>e.scrollBy(0,400));
  await page.getByRole('button',{name:'Locate control',exact:true}).click();
  await expect(page.getByRole('status').filter({hasText:`Step ${step} control located.`})).toBeVisible();
  await expect.poll(async()=>{const r=await spotlight.boundingBox(),c=await page.locator('.st-key-guided_tour').boundingBox();return !!r && r.y>=20 && (r.y+r.height<=c.y || r.x+r.width<=c.x);}).toBe(true);
  const ring=await spotlight.boundingBox(),card=await page.locator('.st-key-guided_tour').boundingBox();
  expect(ring.y).toBeGreaterThanOrEqual(20);
  expect(ring.y+ring.height<=card.y || ring.x+ring.width<=card.x).toBeTruthy();
  if(step===3)await screen(page,'tour-protect.png');
  await page.getByRole('button',{name:step===6?'Finish tour':'Next step',exact:true}).click();
 }
 await expect(spotlight).toHaveCount(0);
 await expect(page.locator('.st-key-guided_tour')).toHaveCount(0);
});
