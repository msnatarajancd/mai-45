// Real Chromium, actual upload/download bytes, isolated fictional data, ZERO model calls.
const {chromium,expect}=require('playwright/test');
const cp=require('child_process'),fs=require('fs'),path=require('path'),crypto=require('crypto');
const python='../.venv/Scripts/python.exe';
const db=path.resolve('node_modules/insurance-browser.sqlite3');
const seed=JSON.parse(cp.execFileSync(python,['-B','tests/fixtures/insurance_browser_seed.py'],{
  env:{...process.env,READYRELIEF_DB_PATH:db},encoding:'utf8'}));
const width=Number(process.env.INSURANCE_BROWSER_WIDTH||1440);
const output='artifacts/insurance-'+(width===390?'mobile':'desktop');
fs.mkdirSync(output,{recursive:true});
async function settled(page){await expect(page.getByTestId('stApp')).not.toHaveAttribute('data-test-script-state','running');await expect(page.getByTestId('stException')).toHaveCount(0);}
async function capture(page,name){await settled(page);await page.getByTestId('stMain').evaluate(e=>e.scrollTop=0);await page.screenshot({path:output+'/'+name+'.png',fullPage:true});}
async function emergency(page){
  for(const control of [page.getByRole('link',{name:'Call 911',exact:true}),page.getByRole('button',{name:"I Can't Call 911",exact:true})]){
    await expect(control).toBeInViewport();
    expect(await control.evaluate(el=>{const r=el.getBoundingClientRect();return el.contains(document.elementFromPoint(r.x+r.width/2,r.y+r.height/2));})).toBe(true);
  }
}
async function click(page,name){await page.getByRole('button',{name,exact:true}).click();await settled(page);}
async function selectStage(page,name){await page.getByText(name,{exact:true}).click();await settled(page);}
async function text(page,name,value){await page.getByRole('textbox',{name,exact:true}).fill(value);}
async function choose(page,name,index){await page.getByRole('combobox',{name,exact:true}).click();await page.keyboard.press('Home');for(let n=0;n<index;n++)await page.keyboard.press('ArrowDown');await page.keyboard.press('Enter');await settled(page);}
async function reopen(page,caseId){
  await page.goto('http://127.0.0.1:8518');await click(page,'Start my recovery');
  await click(page,'Resume My Recovery');await text(page,'Recovery case ID',caseId);await click(page,'Open saved recovery');
  await click(page,'Prepare for insurance');
  await expect(page.getByRole('heading',{name:'Insurance Preparation Workspace',exact:true})).toBeVisible();
}
async function download(page,label,name){const pending=page.waitForEvent('download');await page.getByRole('button',{name:label,exact:true}).click();const file=await pending;await file.saveAs(output+'/'+name);return output+'/'+name;}
(async()=>{
  const browser=await chromium.launch({headless:true,args:['--mute-audio']});
  const page=await browser.newPage({viewport:{width,height:width===390?844:1000}});
  page.setDefaultTimeout(20000);
  await reopen(page,seed.empty);
  await expect(page.getByRole('textbox',{name:'Insurer name (optional)',exact:true})).toBeVisible();
  await expect(page.getByRole('button',{name:'Document damage for insurance',exact:true})).toBeVisible();
  await capture(page,'empty-insurance');await emergency(page);
  await page.reload();await reopen(page,seed.populated);
  await text(page,'Insurer name (optional)','Fictional Demonstration Mutual');
  await text(page,'Policy reference (optional)','SYNTHETIC-POLICY-42');
  await page.getByText('I confirm these Insurance details',{exact:true}).click();await click(page,'Save Insurance Details');
  await selectStage(page,'Damage Inventory');
  await expect(page.getByRole('button',{name:'Edit Details',exact:true})).toHaveCount(2);
  await page.getByRole('button',{name:'Edit Details',exact:true}).first().click();await settled(page);
  await text(page,'Brand (optional)','Synthetic refrigerator brand');
  await text(page,'User-estimated repair / replacement cost (optional)','123.45');
  await text(page,'Currency (three-letter code) (optional)','USD');
  await page.getByText('I confirm these item details',{exact:true}).click();await click(page,'Save Item Details');
  await capture(page,'inventory');
  await selectStage(page,'Evidence & Documents');
  await page.getByRole('combobox',{name:'Associate new evidence with',exact:true}).click();
  await page.keyboard.press('Home');await page.keyboard.press('ArrowDown');await page.keyboard.press('Enter');
  await settled(page);
  const originals=seed.photos.map(b=>Buffer.from(b,'base64'));
  await page.locator('input[type=file]').setInputFiles(originals.map((buffer,i)=>({name:'synthetic-'+i+'.png',mimeType:'image/png',buffer})));
  await expect(page.getByText('Unsaved preview: synthetic-0.png',{exact:true})).toBeVisible();
  await expect(page.getByText('Unsaved preview: synthetic-1.png',{exact:true})).toBeVisible();
  await page.getByText('I confirm saving these attachments',{exact:true}).click();await click(page,'Save Attachments');
  await expect(page.getByRole('button',{name:'Download saved photograph',exact:true})).toHaveCount(2);
  await page.reload();await reopen(page,seed.populated);
  await expect(page.getByRole('textbox',{name:'Insurer name (optional)',exact:true})).toHaveValue('Fictional Demonstration Mutual');
  await selectStage(page,'Evidence & Documents');
  await expect(page.getByRole('button',{name:'Download saved photograph',exact:true})).toHaveCount(2);
  const saved=page.getByRole('button',{name:'Download saved photograph',exact:true});
  for(let i=0;i<2;i++){
    const pending=page.waitForEvent('download');await saved.nth(i).click();const file=await pending;
    await file.saveAs(output+'/saved-'+i+'.png');expect(fs.readFileSync(output+'/saved-'+i+'.png')).toEqual(originals[i]);
  }
  await choose(page,'Evidence type',1);
  await choose(page,'Evidence status',0);
  await text(page,'Evidence description','Synthetic paper receipt available, not uploaded');
  await page.getByText('I confirm this evidence record',{exact:true}).click();await click(page,'Save Evidence Record');
  await choose(page,'Evidence type',2);
  await choose(page,'Evidence status',2);
  await text(page,'Evidence description','Synthetic repair estimate unavailable');
  await page.getByText('I confirm this evidence record',{exact:true}).click();await click(page,'Save Evidence Record');
  await text(page,'Communication reference (optional)','SYNTHETIC-CALL-42');
  await text(page,'Communication summary','User reports a fictional call asking about documents. No submission accepted.');
  await page.getByText('I confirm this user-reported communication',{exact:true}).click();await click(page,'Save Communication');
  await capture(page,'saved-evidence');await emergency(page);
  await selectStage(page,'Review & Download');await capture(page,'review-download');
  await download(page,'Download Preparation PDF','preparation.pdf');
  await download(page,'Download Damage Inventory CSV','inventory.csv');
  const archive=await download(page,'Download Evidence ZIP','evidence.zip');
  const hashes=originals.map(b=>crypto.createHash('sha256').update(b).digest('hex'));
  cp.execFileSync(python,['-B','tests/fixtures/inspect_insurance_downloads.py',output,JSON.stringify(hashes)],{stdio:'inherit'});
  await selectStage(page,'Evidence & Documents');
  await page.getByText('I confirm removing this file',{exact:true}).first().click();
  await page.getByRole('button',{name:'Remove saved photograph',exact:true}).first().click();await settled(page);
  await expect(page.getByRole('button',{name:'Download saved photograph',exact:true})).toHaveCount(1);
  await page.reload();await reopen(page,seed.populated);await selectStage(page,'Evidence & Documents');
  await expect(page.getByRole('button',{name:'Download saved photograph',exact:true})).toHaveCount(1);
  await capture(page,'remaining-saved-photo');
  await page.getByRole('button',{name:'Immediate danger',exact:true}).click();
  await expect(page.getByText('Routine recovery actions are paused.',{exact:false})).toBeVisible();
  await emergency(page);
  const returning=await browser.newPage({viewport:{width,height:width===390?844:1000}});
  await reopen(returning,seed.returning);
  await selectStage(returning,'Damage Inventory');
  await expect(returning.getByRole('button',{name:'Edit Details',exact:true})).toHaveCount(1);
  await click(returning,'Document damage for insurance');
  await click(returning,'Add Damaged Item');
  await text(returning,'Item or area description','Refrigerator');
  await text(returning,'User-reported damage description','New synthetic refrigerator damage, confirmed through Recovery');
  await returning.getByText('I confirm this damage record',{exact:true}).click();
  await click(returning,'Save confirmed damage record');
  await click(returning,'Prepare for insurance');
  await click(returning,'Reload saved Insurance information');
  await selectStage(returning,'Damage Inventory');
  await expect(returning.getByRole('button',{name:'Edit Details',exact:true})).toHaveCount(2);
  await selectStage(returning,'Evidence & Documents');
  await expect(returning.getByRole('button',{name:'Download saved photograph',exact:true})).toHaveCount(1);
  await selectStage(returning,'Review & Download');await capture(returning,'returning-confirmed-damage');
  await download(returning,'Download Preparation PDF','returning-preparation.pdf');
  cp.execFileSync(python,['-B','-c',`from pypdf import PdfReader;from recovery.database import SQLiteRecoveryRepository;from uuid import UUID;r=SQLiteRecoveryRepository(${JSON.stringify(db)});s=r.get_insurance_snapshot(UUID('${seed.returning}'));p=r.get_active_plan(s.case.case_id);assert s.workspace.profile.insurer_name=='Returning Fictional Insurer';assert len(s.attachments)==1;assert len(s.records.damage_records)==2;assert sum(t.status.value=='COMPLETED' for t in p.proposed_tasks)==1;t=' '.join(page.extract_text() for page in PdfReader('${output}/returning-preparation.pdf').pages);assert 'Sofa' in t and 'Refrigerator' in t`]);
  console.log(JSON.stringify({result:'PASS',width,case:seed.populated,photosUploaded:2,originalHashesVerified:hashes,remainingPhotos:1,archive}));
  await browser.close();
})().catch(error=>{console.error(error);process.exit(1);});
