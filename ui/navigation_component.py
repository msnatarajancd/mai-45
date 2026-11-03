"""Browser-local sidebar toggle: no server request or application-state mutation."""
from streamlit.components.v2 import component

_toggle = component(
    'readyrelief_navigation_toggle',
    html='<button type="button" data-nav-toggle aria-label="Hide navigation" aria-expanded="true" aria-controls="stSidebar"><svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" aria-hidden="true"><path d="M4 6h16M4 12h16M4 18h16"/></svg></button>',
    css='''button {display:grid;place-items:center;width:44px;height:44px;border-radius:12px;border:1px solid var(--rr-border);background:var(--rr-surface);color:var(--rr-ink);cursor:pointer;} button:hover {background:var(--rr-soft);} button:active {filter:brightness(.94);} button:focus-visible {outline:2px solid var(--rr-accent);outline-offset:2px;} @media(max-width:700px){button{display:none;}}''',
    js='''export default function({parentElement}) {
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


def render_toggle(key):
    _toggle(key=key)
