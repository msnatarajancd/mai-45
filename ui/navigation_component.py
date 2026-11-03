"""Browser-local sidebar toggle: no server request or application-state mutation."""
from streamlit.components.v2 import component

_toggle = component(
    'readyrelief_navigation_toggle',
    html='<div class="nav-row"><button type="button" data-nav-toggle aria-label="Hide navigation" aria-expanded="true" aria-controls="stSidebar"><svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" aria-hidden="true"><path d="M4 6h16M4 12h16M4 18h16"/></svg></button><strong data-page></strong></div>',
    css='''.nav-row {display:flex;align-items:center;gap:8px;height:44px;} strong {font:600 16px -apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif;color:var(--rr-ink);white-space:nowrap;} button {display:grid;place-items:center;flex:0 0 44px;width:44px;box-sizing:border-box;height:44px;border-radius:12px;border:1px solid transparent;background:transparent;color:var(--rr-ink);cursor:pointer;} button:hover {background:var(--rr-soft);} button:active {filter:brightness(.94);} button:focus-visible {outline:2px solid var(--rr-accent);outline-offset:2px;} @media(max-width:700px){button{display:none;}}''',
    js='''export default function({parentElement, data}) {
        parentElement.querySelector("[data-page]").textContent=data.page;
        const button=parentElement.querySelector('button');
        const root=document.documentElement;
        if (!root.dataset.rrNavCollapsed) {
            try { root.dataset.rrNavCollapsed=sessionStorage.getItem('rr-nav-collapsed') || 'false'; }
            catch (_) { root.dataset.rrNavCollapsed='false'; }
        }
        const sync=()=>{
            const collapsed=root.dataset.rrNavCollapsed==='true';
            button.setAttribute('aria-expanded',String(!collapsed));
            button.setAttribute('aria-label',collapsed?'Show navigation':'Hide navigation');
            button.title=collapsed?'Show navigation':'Hide navigation';
            const sidebar=document.querySelector('[data-testid=stSidebar]');
            if(sidebar) sidebar.inert=collapsed;
        };
        button.onclick=()=>{
            root.dataset.rrNavCollapsed=String(root.dataset.rrNavCollapsed!=='true');
            try {sessionStorage.setItem('rr-nav-collapsed',root.dataset.rrNavCollapsed);} catch (_) {}
            window.dispatchEvent(new Event('rr-navigation-change'));
            window.dispatchEvent(new Event('resize'));
        };
        window.addEventListener('rr-navigation-change',sync);
        sync();
        return ()=>{button.onclick=null;window.removeEventListener('rr-navigation-change',sync);};
    }''',
)


def render_toggle(key, page):
    _toggle(key=key, data={'page': page})
