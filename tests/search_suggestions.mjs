import assert from 'node:assert/strict';
import {readFileSync,existsSync} from 'node:fs';
import {execFileSync} from 'node:child_process';
class Element {
 constructor(){this.style={};this.attrs={};this.children=[];this.listeners={};this.hidden=false;this.value='';}
 setAttribute(k,v){this.attrs[k]=v;} removeAttribute(k){delete this.attrs[k];}
 addEventListener(k,f){this.listeners[k]=f;} removeEventListener(k){delete this.listeners[k];}
 querySelectorAll(){return this.children.filter(c=>c.attrs.role==='option');}
 replaceChildren(){this.children=[];} appendChild(e){this.children.push(e);}
 closest(){return this;} getBoundingClientRect(){return {left:10,bottom:40,width:300};}
 scrollIntoView(){} contains(e){return e===this||this.children.includes(e);} remove(){this.removed=true;}
 blur(){this.listeners.blur?.();}
 fire(type,key){this.listeners[type]?.({key,isComposing:false,preventDefault(){},stopImmediatePropagation(){}});}
}
const input=new Element(),body=new Element(),selections=[];
globalThis.window={innerWidth:800,innerHeight:600,addEventListener(){},removeEventListener(){}};
globalThis.document={body,createElement(){return new Element();},querySelector(){return input;},addEventListener(){},removeEventListener(){}};
globalThis.MutationObserver=class{constructor(f){this.f=f;}observe(){}disconnect(){}};
const source=readFileSync(new URL('../ui/search_assets/search.js',import.meta.url),'utf8');
const {default:render}=await import('data:text/javascript;base64,'+Buffer.from(source).toString('base64'));
// Read the actual Python-owned rules instead of copying another alias/regex list.
const python=process.env.READYRELIEF_PYTHON || (existsSync('.venv/Scripts/python.exe')?'.venv/Scripts/python.exe':existsSync('.venv/bin/python')?'.venv/bin/python':'python');
const searchData=(enabled)=>JSON.parse(execFileSync(python,['-c',`import json; from ui.capabilities import navigation_search_data; print(json.dumps(navigation_search_data(progress_enabled=${enabled?'True':'False'})))`],{encoding:'utf8'}));
const props={parentElement:{isConnected:true},data:searchData(true),setTriggerValue:(k,v)=>selections.push([k,v])};
const first=render(props);let list=body.children.at(-1);
input.fire('focus');assert.equal(list.hidden,true,'Empty focus should not obscure the page');
input.value='tas';input.fire('input');assert.equal(list.children[0].textContent,'Recover');assert.equal(selections.length,0,'Typing must stay client-side');
input.fire('keydown','Enter');assert.deepEqual(selections.pop(),['destination','Recover']);assert.equal(list.hidden,true);
input.value='re';input.fire('input');input.fire('keydown','ArrowUp');assert.equal(input.attrs['aria-activedescendant'],'rr-search-options-'+(list.children.length-1));input.fire('keydown','Enter');assert.deepEqual(selections.pop(),['destination',props.data.pages.filter(item=>(item.page+' '+item.keywords).toLowerCase().includes('re')).at(-1).page]);
input.value='weather';input.fire('input');list.children[0].onclick();assert.deepEqual(selections.pop(),['destination','Protect']);
input.value='Can you open the weather screen?';input.fire('input');list.children[0].onclick();assert.deepEqual(selections.pop(),['destination','Protect']);
for(const [query,page] of [['open recovery','Recover'],['tasks','Recover'],['recovery progress','Recovery Progress'],['open Recover','Recover'],['dashboard','Recovery Progress']]) {
 input.value=query;input.fire('input');assert.equal(list.children.length,1,query+' must have one destination');assert.equal(list.children[0].textContent,page);input.fire('keydown','Enter');assert.deepEqual(selections.pop(),['destination',page]);
}
for(const [destination,focus] of [['Insurance & Documents','Prepare for insurance'],['My Recovery Plan','Continue my recovery']]) {
 input.value='open '+destination;input.fire('input');assert.equal(list.children.length,1);assert.equal(list.children[0].textContent,destination);input.fire('keydown','Enter');
 const selected=selections.pop();assert.deepEqual(selected,['destination',destination]);
 const state=JSON.parse(execFileSync(python,['-c', 'import json,sys; import ui.components as c; c.st.session_state={"page":"Recover","rr_focus":"Document damage"}; c.navigate_destination(sys.argv[1]); print(json.dumps(c.st.session_state))',selected[1]],{encoding:'utf8'}));
 assert.deepEqual(state,{page:'Recover',rr_focus:focus});
}
input.value='unknown';input.fire('input');assert.match(list.children[0].textContent,/No matching/);input.fire('keydown','Escape');assert.equal(list.hidden,true);
const second=render(props);assert.equal(list.removed,true,'Rerenders must remove old dropdowns');list=body.children.at(-1);first();assert.equal(list.removed,undefined,'Late cleanup must not remove current dropdown');second();assert.equal(list.removed,true);assert.equal(input.listeners.input,undefined);
const disabled=render({...props,data:searchData(false)});list=body.children.at(-1);input.value='recovery progress';input.fire('input');assert.match(list.children[0].textContent,/No matching/);disabled();
console.log('Search suggestion regression passed');
