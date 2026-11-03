import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
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
const props={parentElement:{isConnected:true},data:[{page:'Recover',keywords:'tasks progress'},{page:'Protect',keywords:'weather prepare'}],setTriggerValue:(k,v)=>selections.push([k,v])};
const first=render(props);let list=body.children.at(-1);
input.fire('focus');assert.equal(list.hidden,true,'Empty focus should not obscure the page');
input.value='tas';input.fire('input');assert.equal(list.children[0].textContent,'Recover');assert.equal(selections.length,0,'Typing must stay client-side');
input.fire('keydown','Enter');assert.deepEqual(selections.pop(),['destination','Recover']);assert.equal(list.hidden,true);
input.value='re';input.fire('input');input.fire('keydown','ArrowUp');assert.equal(input.attrs['aria-activedescendant'],'rr-search-options-1');input.fire('keydown','Enter');assert.deepEqual(selections.pop(),['destination','Protect']);
input.value='weather';input.fire('input');list.children[0].onclick();assert.deepEqual(selections.pop(),['destination','Protect']);
input.value='unknown';input.fire('input');assert.match(list.children[0].textContent,/No matching/);input.fire('keydown','Escape');assert.equal(list.hidden,true);
const second=render(props);assert.equal(list.removed,true,'Rerenders must remove old dropdowns');list=body.children.at(-1);first();assert.equal(list.removed,undefined,'Late cleanup must not remove current dropdown');second();assert.equal(list.removed,true);assert.equal(input.listeners.input,undefined);
console.log('Search suggestion regression passed');
