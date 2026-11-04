const {defineConfig}=require('playwright/test');
module.exports=defineConfig({
 testDir:'tests/visual', fullyParallel:false, workers:1, timeout:60000,
 expect:{timeout:10000,toHaveScreenshot:{maxDiffPixelRatio:0.005,animations:'disabled'}},
 // Exercise speech events without playing automated tour checks through the user's speakers.
 use:{baseURL:'http://127.0.0.1:8501',browserName:'chromium',launchOptions:{args:['--mute-audio']},reducedMotion:'reduce',trace:'retain-on-failure'},
 projects:[{name:'desktop',use:{viewport:{width:1440,height:1000}}},{name:'tablet',use:{viewport:{width:1024,height:900}}},{name:'mobile',use:{viewport:{width:390,height:844}}}],
 webServer:{command:(process.env.READYRELIEF_PYTHON || 'python')+' -m streamlit run app.py --server.port=8501 --server.address=127.0.0.1 --server.headless=true',url:'http://127.0.0.1:8501/_stcore/health',reuseExistingServer:!process.env.CI,timeout:60000},
 reporter:[['list'],['html',{open:'never'}]]
});
