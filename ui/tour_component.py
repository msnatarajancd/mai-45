"""Native (non-iframe) browser narration and a nonblocking control spotlight."""
from pathlib import Path
from streamlit.components.v2 import component

_ASSETS = Path(__file__).with_name('tour_assets')
_spotlight = component(
    'readyrelief_spoken_tour',
    html='<div class="rr-tour-audio"><label class="rr-voice-label" for="rr-tour-voice">Narrator voice<select id="rr-tour-voice" data-voice aria-label="Narrator voice"></select></label><button type="button" data-listen>Listen to this step</button><button type="button" data-stop>Stop audio</button><button type="button" data-show>Locate control</button><span role="status" aria-live="polite" data-status>Audio is off. Listening is optional.</span></div>',
    css='''
    .rr-tour-audio {display:grid; grid-template-columns:1.2fr .8fr 1fr; align-items:center; gap:6px; font:inherit; color:var(--rr-ink);}
    .rr-voice-label {grid-column:1 / -1;font-size:.875rem;display:grid;gap:5px;}
    select {font:inherit;font-size:.875rem;width:100%;min-width:0;min-height:40px;padding:7px;border:1px solid var(--rr-border);border-radius:10px;background:var(--rr-soft);color:var(--rr-ink);}
    select:focus-visible {outline:2px solid var(--rr-accent);outline-offset:2px;}
    button {font:inherit; font-size:.875rem; color:inherit; background:var(--rr-soft); border:1px solid var(--rr-border, #89978e); border-radius:10px; padding:7px 6px; cursor:pointer; min-height:44px;}
    button:focus-visible {outline:3px solid #5b9c78; outline-offset:3px;}
    button:disabled {opacity:.55; cursor:default;}
    [data-status] {font-size:.875rem; grid-column:1 / -1; opacity:.8;}
    ''',
    js=(_ASSETS / 'tour.js').read_text(encoding='utf-8'),
)


def render_spotlight(*, run, step, target, narration, active):
    _spotlight(key='spoken_tour', data={
        'run': run, 'step': step, 'target': target,
        'narration': narration, 'active': active,
    })
