export default function(component) {
    const { data, parentElement } = component;
    const listen = parentElement.querySelector('[data-listen]');
    const stop = parentElement.querySelector('[data-stop]');
    const show = parentElement.querySelector('[data-show]');
    const status = parentElement.querySelector('[data-status]');
    const synth = window.speechSynthesis;
    const supported = !!(synth && window.SpeechSynthesisUtterance);
    const previous = window.__readyReliefTour;
    // v2 executes again on data changes without first invoking its unmount callback.
    previous?.cleanup?.();
    const state = previous?.run === data.run ? previous : {run:data.run, enabled:false, spoken:null};
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
    const cancel = () => {
        if (utterance) {utterance.onstart = null; utterance.onend = null; utterance.onerror = null;}
        if (supported) synth.cancel();
        clearTimeout(watchdog);
        utterance = null;
    };
    const stopAudio = () => {if (disposed) return; state.enabled = false; cancel(); sayStatus('Audio stopped. Read the guide or press Listen to resume.');};
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
        if (scroll) target.scrollIntoView({block:'start', behavior:window.matchMedia('(prefers-reduced-motion: reduce)').matches ? 'instant' : 'smooth'});
        placeRing();
        return true;
    };
    const speak = () => {
        if (!data.active || !supported || disposed) return;
        cancel();
        // Only a user's Listen gesture enables narration for subsequent steps.
        state.enabled = true;
        state.spoken = data.step;
        utterance = new SpeechSynthesisUtterance(data.narration);
        utterance.lang = 'en-US';
        utterance.rate = 0.95;
        const voice = synth.getVoices().find(v => v.lang.toLowerCase().startsWith('en'));
        if (voice) utterance.voice = voice; // Browser default also supports delayed voice loading.
        utterance.onstart = () => {clearTimeout(watchdog); sayStatus('Reading this step. Stop audio turns narration off.');};
        utterance.onend = () => {clearTimeout(watchdog); sayStatus('Step finished. Narration is on for your next step.');};
        utterance.onerror = () => {if (disposed) return; state.enabled = false; clearTimeout(watchdog); sayStatus('Audio is unavailable or blocked. Read the guide, or press Listen to try again.');};
        sayStatus('Starting narration…');
        try {
            synth.speak(utterance);
            watchdog = setTimeout(() => {
                if (!synth.speaking) {stopAudio(); sayStatus('No browser voice is available. The written guide and highlights still work.');}
            }, 5000);
        } catch (_) {state.enabled = false; sayStatus('Audio is unavailable. The written guide and highlights still work.');}
    };
    listen.disabled = !supported || !data.active;
    stop.disabled = !supported || !data.active;
    show.disabled = !data.active;
    listen.onclick = () => {locate(true); speak();};
    stop.onclick = stopAudio;
    show.onclick = () => {
        if (!locate(true)) {sayStatus('The control is not visible yet. Open this step’s page to continue.'); return;}
        sayStatus(`Step ${data.step + 1} control located. Look for the numbered marker.`);
        if (!window.matchMedia('(prefers-reduced-motion: reduce)').matches) {
            ring.animate?.([{background:'color-mix(in srgb, var(--rr-accent) 22%, transparent)'},{background:'color-mix(in srgb, var(--rr-accent) 5%, transparent)'}], {duration:650, iterations:1});
        }
    };
    if (!data.active) {state.enabled = false; cancel(); sayStatus('Guide paused. Return to this step to see its controls.');}
    else {
        if (!supported) sayStatus('This browser has no spoken narration. The written guide and highlights still work.');
        else if (state.enabled) sayStatus('Narration is on. Press Stop audio to turn it off.');
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
        document.removeEventListener('click', emergency, true);
        document.removeEventListener('visibilitychange', hide);
        window.removeEventListener('scroll', placeRing, true);
        window.removeEventListener('resize', placeRing);
        if (state.cleanup === cleanup) state.cleanup = null;
    };
    state.cleanup = cleanup;
    return cleanup;
}
