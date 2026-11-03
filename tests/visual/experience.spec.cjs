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
  await expect(page.locator('[data-nav-toggle]:visible')).toHaveCount(1);
  const before=await page.locator('.block-container').boundingBox();
  await page.locator('.st-key-toolbar_toggle').getByRole('button',{name:'Hide navigation',exact:true}).click();
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

test('sidebar animates horizontally and reverses without losing its control',async({page},info)=>{
 test.skip(info.project.name==='mobile','Mobile uses its compact navigation menu.');
 await page.emulateMedia({reducedMotion:'no-preference'});
 await ready(page);
 const toggle=page.locator('.st-key-toolbar_toggle button');
 await toggle.click();
 await expect.poll(()=>page.getByTestId('stSidebar').evaluate(e=>e.getAnimations().length)).toBeGreaterThan(0);
 await expect(page.getByTestId('stSidebar')).toBeHidden();
 await expect(toggle).toBeFocused();
 await toggle.click();
 await expect.poll(()=>page.getByTestId('stSidebar').evaluate(e=>Math.round(e.getBoundingClientRect().x))).toBe(0);
 await expect(page.locator('.st-key-nav_Protect button')).toBeInViewport();
 await page.emulateMedia({reducedMotion:'reduce'});
 await toggle.click();
 await expect(page.getByTestId('stSidebar')).toBeHidden();
 expect(await page.getByTestId('stSidebar').evaluate(e=>e.getAnimations().length)).toBe(0);
});
for(const theme of ['bright','dark'])test(`all screens remain readable in ${theme} mode`,async({page},info)=>{
 await ready(page);
 if(theme==='dark')await page.getByRole('button',{name:'Switch to dark mode',exact:true}).click();
 for(const name of ['Home','Protect','Respond','Recover','Household','Evidence','Assistant']){
  await page.getByTestId('stMain').evaluate(e=>e.scrollTop=0);
  if(info.project.name==='mobile'){
   if(!await page.getByTestId('stPopoverBody').isVisible())await page.getByRole('button',{name:'Navigate',exact:true}).click();
   await page.getByTestId('stPopoverBody').getByRole('button',{name,exact:true}).click();
  }else await page.locator('.st-key-nav_'+name+' button').click();
  await expect(page.locator('[data-page]')).toHaveText(name);
  if(info.project.name==='mobile' && await page.getByTestId('stPopoverBody').isVisible())await page.getByRole('button',{name:'Navigate',exact:true}).click();
  await expect(page.getByTestId('stException')).toHaveCount(0);
  await page.getByTestId('stMain').evaluate(e=>e.scrollTop=0);
  expect(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth)).toBeTruthy();
  const clipped=await page.locator('button p').evaluateAll(es=>es.filter(e=>!e.closest('.st-key-chat_launcher,.st-key-mobile_nav,.st-key-theme_toggle,.st-key-quick_tour')&&e.getBoundingClientRect().width&&getComputedStyle(e).visibility!=='hidden'&&e.scrollWidth>e.clientWidth+2).map(e=>e.textContent));
  expect(clipped,`${name} clipped button labels`).toEqual([]);
  await page.getByTestId('stMain').evaluate(e=>e.scrollTop=e.scrollHeight);
  await expect(page.locator('.rr-footer')).toBeInViewport();
 }
 if(info.project.name!=='mobile'){
  const guide=page.getByRole('button',{name:'Show me around',exact:true});
  await guide.hover();
  const caption=await page.locator('.st-key-sidebar_guide [data-testid=stCaptionContainer]').boundingBox(),button=await guide.boundingBox();
  expect(caption.y+caption.height).toBeLessThanOrEqual(button.y);
  await expect(page.getByTestId('stSidebar')).toHaveScreenshot(`sidebar-hover-${theme}.png`);
 }
});

test('sparkle launcher and chat controls fit the viewport',async({page})=>{
 await ready(page);
 const launcher=page.getByRole('button',{name:'Ask ReadyRelief',exact:true});
 await expect(launcher).toBeVisible();
 const r=await launcher.boundingBox();expect(r.width).toBe(56);expect(r.height).toBe(56);
 await launcher.click();
 const panel=page.locator('.st-key-chat_panel');await expect(panel).toBeVisible();
 const bounds=await panel.boundingBox(),viewport=page.viewportSize();
 expect(bounds.x).toBeGreaterThanOrEqual(0);expect(bounds.x+bounds.width).toBeLessThanOrEqual(viewport.width);
 await expect(page.getByRole('button',{name:'Expand chat',exact:true})).toBeVisible();
 await screen(page,'chat-panel.png');
 await page.getByRole('button',{name:'Expand chat',exact:true}).click();
 await expect(page.getByRole('button',{name:'Minimize chat',exact:true})).toBeVisible();
 await page.getByRole('button',{name:'Minimize chat',exact:true}).click();
 await expect(panel).toBeVisible();
 await page.getByRole('button',{name:'Close chat',exact:true}).click();
 await expect(launcher).toBeVisible();
});
