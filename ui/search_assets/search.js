export default function({data, parentElement, setTriggerValue}) {
    window.__rrSearchCleanup?.();
    let input=null, disposed=false, observer=null, list=null, active=-1, matches=[];
    const id='rr-search-options';
    const close=()=>{if(list)list.hidden=true;input?.setAttribute('aria-expanded','false');input?.removeAttribute('aria-activedescendant');active=-1;};
    const position=()=>{
        if(!input || !list || list.hidden)return;
        const field=input.closest('[data-testid="stTextInputRootElement"]') || input;
        const r=field.getBoundingClientRect();
        list.style.left=`${Math.max(8,r.left)}px`; list.style.top=`${r.bottom+8}px`;
        list.style.width=`${Math.min(r.width,window.innerWidth-16)}px`;
        list.style.maxHeight=`${Math.max(80,Math.min(340,window.innerHeight-r.bottom-20))}px`;
    };
    const choose=(page)=>{close();input.blur();setTriggerValue('destination',page);};
    const highlight=()=>{
        Array.from(list.querySelectorAll('[role="option"]')).forEach((el,i)=>{
            el.setAttribute('aria-selected',String(i===active));
            el.style.background=i===active?'var(--rr-selected)':'transparent';
            if(i===active){input.setAttribute('aria-activedescendant',el.id);el.scrollIntoView({block:'nearest'});}
        });
    };
    const update=()=>{
        if(disposed)return;
        const terms=input.value.trim().toLocaleLowerCase().split(/\s+/).filter(Boolean);
        if(!terms.length){matches=[];close();return;}
        matches=data.filter(item=>terms.every(term=>(item.page+' '+item.keywords).toLocaleLowerCase().includes(term)));
        list.replaceChildren();active=-1;
        if(!matches.length){const empty=document.createElement('div');empty.textContent='No matching screens. Try tasks, weather or family.';empty.setAttribute('role','status');empty.style.cssText='padding:14px;font-size:13px;color:var(--rr-muted)';list.appendChild(empty);}
        matches.forEach((item,i)=>{
            const option=document.createElement('div');option.id=id+'-'+i;option.setAttribute('role','option');option.setAttribute('aria-selected','false');
            option.style.cssText='padding:11px 14px;border-radius:10px;cursor:pointer;font:500 14px -apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif;color:var(--rr-ink)';
            option.textContent=item.page;
            option.onpointerdown=e=>e.preventDefault();
            option.onclick=()=>choose(item.page);
            option.onpointermove=()=>{active=i;highlight();};
            list.appendChild(option);
        });
        list.hidden=false;input.setAttribute('aria-expanded','true');input.removeAttribute('aria-activedescendant');position();
    };
    const keydown=e=>{
        if(e.isComposing)return;
        if(e.key==='Escape'){e.preventDefault();e.stopImmediatePropagation();close();return;}
        if(e.key==='ArrowDown'||e.key==='ArrowUp'){
            e.preventDefault();e.stopImmediatePropagation();if(list.hidden)update();
            if(matches.length){active=active<0?(e.key==='ArrowDown'?0:matches.length-1):(active+(e.key==='ArrowDown'?1:-1)+matches.length)%matches.length;highlight();}
        }else if(e.key==='Enter'&&!list.hidden&&matches.length){
            e.preventDefault();e.stopImmediatePropagation();choose(matches[active<0?0:active].page);
        }else if(e.key==='Tab')close();
    };
    const outside=e=>{if(input&&!input.contains(e.target)&&!list?.contains(e.target))close();};
    const blur=()=>close();
    const bind=()=>{
        const found=document.querySelector('.st-key-nav_search input');
        if(found===input)return;
        detach();input=found;
        if(!input)return;
        input.setAttribute('role','combobox');input.setAttribute('aria-autocomplete','list');input.setAttribute('aria-controls',id);input.setAttribute('aria-expanded','false');
        input.addEventListener('input',update);input.addEventListener('focus',update);input.addEventListener('keydown',keydown,true);input.addEventListener('blur',blur);
    };
    const detach=()=>{
        if(!input)return;
        input.removeEventListener('input',update);input.removeEventListener('focus',update);input.removeEventListener('keydown',keydown,true);input.removeEventListener('blur',blur);
        for(const attr of ['role','aria-autocomplete','aria-controls','aria-expanded','aria-activedescendant'])input.removeAttribute(attr);
        close();input=null;
    };
    list=document.createElement('div');list.id=id;list.setAttribute('role','listbox');list.setAttribute('aria-label','Suggested screens');list.hidden=true;
    list.style.cssText='position:fixed;z-index:1100;box-sizing:border-box;padding:6px;background:var(--rr-surface);border:1px solid var(--rr-border);border-radius:14px;box-shadow:0 12px 36px var(--rr-shadow);overflow-y:auto;';
    document.body.appendChild(list);bind();
    const cleanup=()=>{if(disposed)return;disposed=true;observer?.disconnect();detach();list.remove();document.removeEventListener('pointerdown',outside,true);window.removeEventListener('resize',position);window.removeEventListener('scroll',position,true);if(window.__rrSearchCleanup===cleanup)window.__rrSearchCleanup=null;};
    observer=new MutationObserver(()=>{if(!parentElement.isConnected)cleanup();else bind();});
    observer.observe(document.body,{childList:true,subtree:true});
    document.addEventListener('pointerdown',outside,true);window.addEventListener('resize',position);window.addEventListener('scroll',position,true);
    window.__rrSearchCleanup=cleanup;
    return cleanup;
}
