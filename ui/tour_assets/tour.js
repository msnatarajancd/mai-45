export default function(component) {
    const { data, parentElement } = component;
    const listen = parentElement.querySelector('[data-listen]');
    const stop = parentElement.querySelector('[data-stop]');
    const show = parentElement.querySelector('[data-show]');
    const status = parentElement.querySelector('[data-status]');
    const voicePicker = parentElement.querySelector('[data-voice]');
    const voiceInfo = parentElement.querySelector('[data-voice-info]');
    let voices = [];
    let preferredVoice = window.__rrTourVoice || '';
    try { preferredVoice = preferredVoice || window.sessionStorage.getItem('rr-tour-voice') || ''; } catch (_) {}
    const synth = window.speechSynthesis;
    const supported = !!(synth && window.SpeechSynthesisUtterance);
    const previous = window.__readyReliefTour;
    // v2 executes again on data changes without first invoking its unmount callback.
    previous?.cleanup?.();
    const state = previous?.run === data.run ? previous : {run:data.run, enabled:true, spoken:null};
    window.__readyReliefTour = state;
    let disposed = false, target = null, timer = null, watchdog = null, utterance = null;
    const ring = document.createElement('div');
    ring.setAttribute('aria-hidden', 'true');
    ring.setAttribute('data-testid', 'rr-tour-spotlight');
    Object.assign(ring.style, {position:'fixed', pointerEvents:'none', border:'1px solid var(--rr-accent, #087f6c)', borderRadius:'10px', background:'color-mix(in srgb, var(--rr-accent) 5%, transparent)', boxShadow:'0 4px 18px var(--rr-shadow)', zIndex:'100', display:'none', boxSizing:'border-box'});
    const marker = document.createElement('span');
    marker.textContent = `Step ${data.step + 1}`;
    Object.assign(marker.style, {position:'absolute', top:'-22px', left:'8px', background:'var(--rr-accent)', color:'var(--rr-onaccent)', borderRadius:'6px', padding:'3px 9px', font:'600 12px system-ui', whiteSpace:'nowrap'});
    ring.appendChild(marker);
    document.body.appendChild(ring);
    const sayStatus = (message) => {if (!disposed) status.textContent = message;};
    const updateMute = () => {
        stop.textContent = state.enabled ? 'Mute narration' : 'Unmute narration';
        stop.setAttribute('aria-pressed', String(!state.enabled));
    };
    const cancel = () => {
        if (utterance) {utterance.onstart = null; utterance.onend = null; utterance.onerror = null;}
        if (supported) synth.cancel();
        clearTimeout(watchdog);
        utterance = null;
    };
    const stopAudio = () => {if (disposed) return; state.enabled = false; cancel(); updateMute(); sayStatus('Narration muted. It will stay muted as you move between steps.');};
    const placeRing = () => {
        if (disposed) return;
        if (!target?.isConnected || !data.active) {ring.style.display = 'none'; return;}
        const rect = target.getBoundingClientRect();
        Object.assign(ring.style, {display: rect.width && rect.height ? 'block' : 'none', left:`${rect.left-5}px`, top:`${rect.top-5}px`, width:`${rect.width+10}px`, height:`${rect.height+10}px`});
    };
    const locate = (scroll) => {
        if (disposed) return false;
        target = data.active ? document.querySelector(data.target) : null;
        if (!target) return false;
        const header = document.querySelector('.st-key-top_toolbar')?.getBoundingClientRect();
        const emergency = document.querySelector('.st-key-emergency_bar')?.getBoundingClientRect();
        const guide = document.querySelector('.st-key-guided_tour')?.getBoundingClientRect();
        // Reserve room for both persistent controls and the numbered marker.
        const top = Math.max(0, header?.bottom || 0, emergency?.bottom || 0) + 32;
        const rect = target.getBoundingClientRect();
        const bottom = guide && rect.right > guide.left && rect.left < guide.right ? guide.top : window.innerHeight;
        if (rect.height + 10 > bottom - top) {
            // A whole card may not fit between the sticky actions and mobile
            // tour. Highlight its actual control without focusing or clicking it.
            const control = target.querySelector('button:not([disabled])') || target.querySelector('input,select,[role="combobox"],a[href]');
            if (control?.getBoundingClientRect().height) target = control;
        }
        if (scroll) {
            const behavior = window.matchMedia('(prefers-reduced-motion: reduce)').matches ? 'instant' : 'smooth';
            const main = target.closest('[data-testid="stMain"]');
            if (main) main.scrollBy({top:target.getBoundingClientRect().top - top, behavior});
            else target.scrollIntoView({block:'start', behavior});
        }
        placeRing();
        return true;
    };
    const speak = () => {
        if (!data.active || !supported || disposed) return;
        cancel();
        // A new tour speaks automatically; explicit mute survives step changes.
        state.enabled = true;
        updateMute();
        const voice = voices.find(v => v.voiceURI === voicePicker.value);
        if (!voice) {sayStatus('Waiting for browser voices…'); return;}
        state.spoken = data.step;
        utterance = new SpeechSynthesisUtterance(data.narration);
        utterance.lang = 'en-US';
        utterance.rate = 1.0;
        utterance.voice = voice;
        utterance.onstart = () => {clearTimeout(watchdog); sayStatus('Reading this step. Use Mute narration to stop.');};
        utterance.onend = () => {clearTimeout(watchdog); sayStatus('Step finished. Narration is on for your next step.');};
        utterance.onerror = () => {if (disposed) return; state.enabled = false; clearTimeout(watchdog); updateMute(); sayStatus('Your browser blocked or could not play narration. Use Unmute narration to retry.');};
        sayStatus('Starting narration…');
        try {
            watchdog = setTimeout(() => {
                if (!synth.speaking) {stopAudio(); sayStatus('Narration did not start. Use Unmute narration to retry; the written guide still works.');}
            }, 5000);
            synth.speak(utterance);
        } catch (_) {state.enabled = false; updateMute(); sayStatus('Audio is unavailable. Use Unmute narration to retry.');}
    };
    const populateVoices = () => {
        if(disposed) return;
        voices = supported ? synth.getVoices().filter(v => v.lang.toLowerCase().startsWith('en')) : [];
        voices.sort((a,b) => Number(b.localService === true)-Number(a.localService === true) || Number(/natural|neural/i.test(b.name))-Number(/natural|neural/i.test(a.name)) || a.name.localeCompare(b.name));
        voicePicker.replaceChildren();
        for(const voice of voices) {
            const option=document.createElement('option');option.value=voice.voiceURI;
            const gender=/Microsoft (David|Mark)\b/i.test(voice.name)?' · Male':/Microsoft Zira\b/i.test(voice.name)?' · Female':'';
            const service = voice.localService === true ? 'On-device' : voice.localService === false ? 'Online' : 'Service unknown';
            option.textContent=voice.name.replace(/ - English \(.*\)/,'')+gender+' · '+service;
            voicePicker.appendChild(option);
        }
        if(!voices.length){const option=document.createElement('option');option.textContent='Waiting for browser voices';option.value='';voicePicker.appendChild(option);}
        voicePicker.value=voices.some(v=>v.voiceURI===preferredVoice)?preferredVoice:(voices[0]?.voiceURI || '');
        voicePicker.disabled=!supported || !voices.length;
        describeVoice();
        if (state.enabled && state.spoken !== data.step && target) speak();
    };
    const describeVoice = () => {
        const voice = voices.find(v => v.voiceURI === voicePicker.value);
        voiceInfo.textContent = !voice ? 'Voice availability depends on your browser.' : voice.localService === true ? 'On-device speech, as reported by your browser.' : voice.localService === false ? 'Online voice: narration text is processed by the voice provider.' : 'Your browser does not identify where this voice is processed.';
    };
    populateVoices();
    synth?.addEventListener?.('voiceschanged',populateVoices);
    voicePicker.onchange=()=>{
        preferredVoice=voicePicker.value;window.__rrTourVoice=preferredVoice;
        try {window.sessionStorage.setItem('rr-tour-voice',preferredVoice);}catch(_){}
        describeVoice();
        if(state.enabled) speak();
        else sayStatus('Voice selected. Narration stays muted until you unmute.');
    };
    listen.disabled = !supported || !data.active;
    stop.disabled = !supported || !data.active;
    show.disabled = !data.active;
    listen.onclick = () => {locate(true); speak();};
    stop.onclick = () => {if(state.enabled) stopAudio(); else {locate(true); speak();}};
    updateMute();
    show.onclick = () => {
        if (!locate(true)) {sayStatus('The control is not visible yet. Open this step’s page to continue.'); return;}
        sayStatus(`Step ${data.step + 1} control located. Look for the numbered marker.`);
        if (!window.matchMedia('(prefers-reduced-motion: reduce)').matches) {
            ring.animate?.([{background:'color-mix(in srgb, var(--rr-accent) 22%, transparent)'},{background:'color-mix(in srgb, var(--rr-accent) 5%, transparent)'}], {duration:650, iterations:1});
        }
    };
    if (!data.active) {cancel(); sayStatus('Guide paused. Return to this step to see its controls.');}
    else {
        if (!supported) sayStatus('This browser has no spoken narration. The written guide and highlights still work.');
        else if (state.enabled) sayStatus('Narration starts automatically. You can mute it at any time.');
        else sayStatus('Narration is muted. Use Unmute narration to hear this step.');
        let attempts = 0;
        const seek = () => {
            if (disposed) return;
            if (locate(true)) {
                if (state.enabled && state.spoken !== data.step) speak();
            } else if (++attempts < 30) timer = setTimeout(seek, 150);
            else sayStatus('Use the written directions below; this control is not visible yet.');
        };
        timer = setTimeout(seek, 100);
    }
    const emergency = (event) => {
        const control = event.target.closest?.('button,a');
        if (control?.closest('.st-key-emergency_bar') || control?.getAttribute('href')?.startsWith('tel:')) {
            stopAudio(); ring.style.display = 'none'; clearTimeout(timer); target = null;
        }
    };
    const hide = () => {if (document.hidden) stopAudio();};
    document.addEventListener('click', emergency, true);
    document.addEventListener('visibilitychange', hide);
    window.addEventListener('scroll', placeRing, true);
    window.addEventListener('resize', placeRing);
    const observer = new MutationObserver(() => {
        if (disposed) return;
        if (!parentElement.isConnected) cleanup();
        else locate(false);
    });
    observer.observe(document.body, {childList:true, subtree:true});
    const cleanup = () => {
        if (disposed) return;
        disposed = true; cancel(); clearTimeout(timer); observer.disconnect(); ring.remove();
        synth?.removeEventListener?.('voiceschanged',populateVoices);voicePicker.onchange=null;
        document.removeEventListener('click', emergency, true);
        document.removeEventListener('visibilitychange', hide);
        window.removeEventListener('scroll', placeRing, true);
        window.removeEventListener('resize', placeRing);
        if (state.cleanup === cleanup) state.cleanup = null;
    };
    state.cleanup = cleanup;
    return cleanup;
}
