import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
const rings = new Set();
const observers = [];
let cancellations = 0;
globalThis.window = {speechSynthesis:{cancel(){cancellations++;},getVoices(){return [];},speak(){}},SpeechSynthesisUtterance:class {},addEventListener(){},removeEventListener(){}};
globalThis.document = {body:{appendChild(el){rings.add(el);}},createElement(){return {style:{},appendChild(){},setAttribute(){},remove(){rings.delete(this);}};},addEventListener(){},removeEventListener(){}};
globalThis.MutationObserver = class {constructor(fn){this.fn=fn;observers.push(this);} observe(){} disconnect(){this.disconnected=true;}};
const source=readFileSync(new URL('../ui/tour_assets/tour.js',import.meta.url),'utf8');
const {default:render}=await import('data:text/javascript;base64,'+Buffer.from(source).toString('base64'));
function mount(step){
 const nodes={}; const parentElement={isConnected:true,querySelector(selector){return nodes[selector]??= {replaceChildren(){},appendChild(){}};}};
 return {parentElement,cleanup:render({parentElement,data:{run:'one',step,active:false}})};
}
const first=mount(0);
assert.equal(rings.size,1);
const second=mount(1);
assert.equal(rings.size,1,'A data update must replace its old spotlight');
const before=cancellations;
first.cleanup();
assert.equal(cancellations,before,'A late old cleanup must not stop the current narration');
assert.equal(rings.size,1);
second.parentElement.isConnected=false;
observers.at(-1).fn();
assert.equal(rings.size,0,'Removing the tour must remove its spotlight');
assert.ok(observers.every(o=>o.disconnected));
second.cleanup();
assert.equal(rings.size,0);
console.log('Tour lifecycle regression passed');
