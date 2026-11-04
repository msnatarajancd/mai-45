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
test('search and chat route consistently without turning search into AI',async({page})=>{
 await ready(page);
 const search=page.getByRole('combobox',{name:'Search menu',exact:true});
 await search.fill('open weather');
 await expect(page.getByRole('option',{name:'Protect',exact:true})).toBeVisible();
 await search.press('Enter');
 await expect(page.getByRole('button',{name:'Show simulated alert',exact:true})).toBeVisible();
 await page.getByRole('button',{name:'Ask ReadyRelief',exact:true}).click();
 const input=page.locator('.st-key-chat_panel textarea');
 await input.fill('go to the family page');await input.press('Enter');
 await expect(page.getByRole('button',{name:'Save household preferences',exact:true})).toBeVisible();
 await expect(page.locator('.st-key-chat_panel')).toHaveCount(0);
 await search.fill('why does the moon glow');
 await expect(page.getByRole('status').filter({hasText:'No matching screens.'})).toBeVisible();
 await search.press('Enter');
 await expect(page.getByRole('button',{name:'Save household preferences',exact:true})).toBeVisible();
 await expect(page.locator('.st-key-chat_panel')).toHaveCount(0);
});

test('tour locates every control and cleans up',async({page})=>{
 await ready(page);
 await page.getByRole('button',{name:'Start walkthrough',exact:true}).click();
 await expect(page.locator('.st-key-tour_welcome')).toBeInViewport();
 await screen(page,'tour-welcome.png');
 await page.getByRole('button',{name:'Start exploring',exact:true}).click();
 const spotlight=page.getByTestId('rr-tour-spotlight');
 for(let step=1;step<=6;step++){
  await expect(page.locator('.st-key-guided_tour')).toContainText(`STEP ${step} OF 6`);
  await expect(spotlight).toBeVisible();
  if(step===3)await page.getByTestId('stMain').evaluate(e=>e.scrollBy(0,400));
  await page.getByRole('button',{name:'Locate control',exact:true}).click();
  await expect(page.getByRole('status').filter({hasText:`Step ${step} control located.`})).toBeVisible();
  await expect.poll(async()=>{const r=await spotlight.boundingBox(),c=await page.locator('.st-key-guided_tour').boundingBox();return !!r && r.y>=20 && (r.y+r.height<=c.y || r.x+r.width<=c.x);}).toBe(true);
  const ring=await spotlight.boundingBox(),card=await page.locator('.st-key-guided_tour').boundingBox();
  expect(ring.y).toBeGreaterThanOrEqual((await page.locator(".st-key-top_toolbar").boundingBox()).height);
  expect(ring.y+ring.height<=card.y || ring.x+ring.width<=card.x).toBeTruthy();
  if(step===3)await screen(page,'tour-protect.png');
  await page.getByRole('button',{name:step===6?'Finish tour':'Next step',exact:true}).click();
 }
 await expect(spotlight).toHaveCount(0);
 await expect(page.locator('.st-key-guided_tour')).toHaveCount(0);
});

test('guided demo visibly starts, advances and restarts',async({page},info)=>{
 await ready(page);
 const launch=async()=>{
  if(info.project.name==='mobile'){
   await page.getByRole('button',{name:'ReadyRelief home',exact:true}).click();
   await page.getByRole('button',{name:'Meet the demo household',exact:true}).click();
  }else await page.getByRole('button',{name:'Start guided demo',exact:true}).click();
 };
 await launch();
 const welcome=page.locator('.st-key-tour_welcome');
 await expect(welcome).toBeInViewport();
 await expect(welcome).toContainText('Meet the Rivera household.');
 await expect(welcome).toContainText('No live requests or recovery changes made.');
 await expect(page.getByRole('button',{name:'Start demo tour',exact:true})).toBeInViewport({ratio:1});
 await screen(page,'demo-welcome.png');
 await page.getByRole('button',{name:'Start demo tour',exact:true}).click();
 for(const [index,name] of ['Protect','Respond','Recover'].entries()){
  await expect(page.locator('.st-key-guided_tour')).toContainText(`STEP ${index+1} OF 3 · ${name.toUpperCase()}`);
  await expect(page.getByTestId('stApp')).not.toHaveAttribute('data-test-script-state','running');
  await expect(page.getByTestId('rr-tour-spotlight')).toBeVisible();
  await page.getByRole('button',{name:'Locate control',exact:true}).click();
  await expect(page.getByRole('status').filter({hasText:`Step ${index+1} control located.`})).toBeVisible();
  await page.getByRole('button',{name:index===2?'Finish tour':'Next step',exact:true}).click();
 }
 await expect(page.locator('.st-key-guided_tour')).toHaveCount(0);
 await launch();
 await expect(welcome).toBeInViewport();
 await page.getByRole('button',{name:'End tour',exact:true}).click();
 await expect(welcome).toHaveCount(0);
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

test('header and branding stay fixed while the page scrolls',async({page},info)=>{
 await ready(page);
 const header=page.locator('.st-key-top_toolbar'),brand=page.locator('.st-key-header_brand');
 const before=await header.boundingBox();
 await page.getByTestId('stMain').evaluate(e=>e.scrollTop=e.scrollHeight);
 await expect(header).toBeInViewport();await expect(brand).toBeInViewport();
 expect((await header.boundingBox()).y).toBe(before.y);
 expect(before.y).toBe(0);
 await expect(page.getByRole('combobox',{name:'Search menu',exact:true})).toBeInViewport();
 if(info.project.name!=='mobile'){
  expect((await page.getByTestId('stSidebar').boundingBox()).y).toBeGreaterThanOrEqual(before.height);
  await page.locator('.st-key-toolbar_toggle button').click();
  await expect(brand).toBeInViewport();expect((await header.boundingBox()).y).toBe(0);
 }
 await screen(page,'header-scrolled.png');
});
test('narration starts automatically and mute persists between steps',async({page})=>{
 // Test doubles verify selection and orchestration, not perceived voice quality.
 await page.addInitScript(()=>{
  window.__spoken=[];
  window.SpeechSynthesisUtterance=class {constructor(text){this.text=text;}};
  Object.defineProperty(window,'speechSynthesis',{value:{
   getVoices:()=>[{name:'Google English',voiceURI:'google',lang:'en-US',localService:false},{name:'Microsoft David - English (United States)',voiceURI:'david',lang:'en-US',localService:true},{name:'Microsoft Zira - English (United States)',voiceURI:'zira',lang:'en-US',localService:true}],
   cancel(){},addEventListener(){},removeEventListener(){},
   speak(u){window.__spoken.push({voice:u.voice.voiceURI,text:u.text});u.onstart?.();},speaking:true
  }});
 });
 await ready(page);
 await page.getByRole('button',{name:'Start walkthrough',exact:true}).click();
 await page.getByRole('button',{name:'Start exploring',exact:true}).click();
 const voices=page.getByRole('combobox',{name:'Narrator voice',exact:true});
 await expect(voices).toBeVisible();
 await expect(voices).toContainText('Male');await expect(voices).toContainText('Female');
 await expect.poll(()=>page.evaluate(()=>window.__spoken.at(-1)?.voice)).toBe('david');
 await expect(voices).toContainText('On-device');await expect(voices).toContainText('Online');
 await voices.selectOption('zira');
 await expect.poll(()=>page.evaluate(()=>window.__spoken.at(-1)?.voice)).toBe('zira');
 await page.getByRole('button',{name:'Next step',exact:true}).click();
 await expect(voices).toHaveValue('zira');
 await voices.selectOption('david');
 await expect.poll(()=>page.evaluate(()=>window.__spoken.at(-1)?.voice)).toBe('david');
 await page.getByRole('button',{name:'Mute narration',exact:true}).click();
 const count=await page.evaluate(()=>window.__spoken.length);
 await page.getByRole('button',{name:'Next step',exact:true}).click();
 await expect(page.locator('.st-key-guided_tour')).toContainText('STEP 3');
 await expect(page.getByTestId('rr-tour-spotlight')).toBeVisible();
 await expect(page.getByRole('button',{name:'Unmute narration',exact:true})).toHaveAttribute('aria-pressed','true');
 expect(await page.evaluate(()=>window.__spoken.length)).toBe(count);
 await voices.selectOption('google');
 await expect(page.locator('[data-voice-info]')).toContainText('processed by the voice provider');
 expect(await page.evaluate(()=>window.__spoken.length)).toBe(count);
 await page.getByRole('button',{name:'Unmute narration',exact:true}).click();
 await expect.poll(()=>page.evaluate(()=>window.__spoken.at(-1)?.voice)).toBe('google');
 await page.getByRole('button',{name:'Mute narration',exact:true}).click();
 await page.getByRole('button',{name:'End tour',exact:true}).click();
 await page.getByRole('button',{name:'Start walkthrough',exact:true}).click();
 await page.getByRole('button',{name:'Start exploring',exact:true}).click();
 await expect.poll(()=>page.evaluate(()=>window.__spoken.length)).toBeGreaterThan(count+1);
});

test('delayed voices and blocked autoplay provide a working retry',async({page})=>{
 await page.addInitScript(()=>{
  window.__availableVoices=[];window.__voiceListener=null;window.__attempts=0;
  window.SpeechSynthesisUtterance=class {constructor(text){this.text=text;}};
  Object.defineProperty(window,'speechSynthesis',{value:{
   getVoices:()=>window.__availableVoices,
   addEventListener(event,fn){if(event==='voiceschanged')window.__voiceListener=fn;},
   removeEventListener(){window.__voiceListener=null;},cancel(){},speaking:false,
   speak(u){window.__attempts++;if(window.__attempts===1)u.onerror?.({error:'not-allowed'});else u.onstart?.();}
  }});
 });
 await ready(page);
 await page.getByRole('button',{name:'Start walkthrough',exact:true}).click();
 await page.getByRole('button',{name:'Start exploring',exact:true}).click();
 await expect(page.getByTestId('rr-tour-spotlight')).toBeVisible();
 expect(await page.evaluate(()=>window.__attempts)).toBe(0);
 await page.evaluate(()=>{window.__availableVoices=[{name:'Microsoft Zira',voiceURI:'zira',lang:'en-US',localService:true}];window.__voiceListener();});
 await expect(page.locator('[data-status]')).toContainText('blocked or could not play');
 await page.getByRole('button',{name:'Unmute narration',exact:true}).click();
 await expect(page.locator('[data-status]')).toContainText('Reading this step');
 expect(await page.evaluate(()=>window.__attempts)).toBe(2);
 await page.getByRole('button',{name:'End tour',exact:true}).click();
});

test('header controls share one centerline',async({page},info)=>{
 await ready(page);
 const selectors=info.project.name==='mobile'
  ? ['.st-key-mobile_nav button','.st-key-nav_search [data-testid="stTextInputRootElement"]','.st-key-theme_toggle button','.st-key-quick_tour button']
  : ['.rr-brand','.st-key-toolbar_toggle button','.st-key-nav_search [data-testid="stTextInputRootElement"]','.st-key-theme_toggle button','.st-key-quick_tour button'];
 const centers=[];
 for(const selector of selectors){const control=page.locator(selector+':visible').first();await expect(control).toBeVisible();const box=await control.boundingBox();centers.push(box.y+box.height/2);}
 expect(Math.max(...centers)-Math.min(...centers)).toBeLessThanOrEqual(3);
});

test('brand returns home with pointer and keyboard',async({page})=>{
 await ready(page);
 await page.getByRole('button',{name:'Explore your next step',exact:true}).click();
 await expect(page.getByRole('button',{name:'Show simulated alert',exact:true})).toBeVisible();
 const brand=page.getByRole('button',{name:'ReadyRelief home',exact:true});
 await brand.click();
 await expect(page.getByRole('button',{name:'Explore your next step',exact:true})).toBeVisible();
 await page.getByRole('button',{name:'Explore your next step',exact:true}).click();
 await expect(page.getByRole('button',{name:'Show simulated alert',exact:true})).toBeVisible();
 await brand.focus();await brand.press('Enter');
 await expect(page.getByRole('button',{name:'Explore your next step',exact:true})).toBeVisible();
});

test('branded loading indicator follows processing state',async({page})=>{
 await ready(page);
 const indicator=page.locator('.st-key-app_loading');
 await expect(indicator).toBeHidden();
 // Deterministic visual state coverage; real server transitions are checked separately.
 await page.getByTestId('stApp').evaluate(e=>e.setAttribute('data-test-script-state','running'));
 await expect(indicator).toBeVisible();
 await expect(indicator).toContainText('Working on your request');
 await expect(indicator).toHaveCSS('pointer-events','none');
 await expect(indicator).toHaveScreenshot('loading-indicator.png');
 await page.getByTestId('stApp').evaluate(e=>e.setAttribute('data-test-script-state','notRunning'));
 await expect(indicator).toBeHidden();
});
