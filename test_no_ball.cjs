const { spawn } = require('child_process');
const http = require('http');
const fs = require('fs');

async function testScreenshots() {
  const edgePath = 'C:\\Program Files (x86)\\Microsoft\\Edge\\Application\\msedge.exe';
  const cdpPort = 9227;
  const edge = spawn(edgePath, [
    `--remote-debugging-port=${cdpPort}`,
    '--headless=new',
    '--disable-gpu',
    '--no-first-run',
    '--no-default-browser-check',
    '--window-size=1280,900',
    'http://127.0.0.1:3005'
  ]);

  await new Promise(r => setTimeout(r, 2000));

  function cdpRequest(endpoint) {
    return new Promise((resolve, reject) => {
      http.get(`http://127.0.0.1:${cdpPort}${endpoint}`, (res) => {
        let data = '';
        res.on('data', chunk => data += chunk);
        res.on('end', () => {
          try { resolve(JSON.parse(data)); } catch(e) { resolve(data); }
        });
      }).on('error', reject);
    });
  }

  try {
    const list = await cdpRequest('/json');
    const target = list.find(t => t.url && t.url.includes('3005')) || list[0];
    const ws = new WebSocket(target.webSocketDebuggerUrl);
    await new Promise(r => ws.addEventListener('open', r, { once: true }));

    let msgId = 1;
    function send(method, params = {}) {
      return new Promise((resolve) => {
        const id = msgId++;
        const handler = (evt) => {
          const res = JSON.parse(evt.data);
          if (res.id === id) {
            ws.removeEventListener('message', handler);
            resolve(res.result?.result || res.result);
          }
        };
        ws.addEventListener('message', handler);
        ws.send(JSON.stringify({ id, method, params }));
      });
    }

    // Wait for React to mount
    for (let i = 0; i < 20; i++) {
      const check = await send('Runtime.evaluate', {
        expression: "!!document.querySelector('#root > div')",
        returnByValue: true
      });
      if (check.value) break;
      await new Promise(r => setTimeout(r, 250));
    }

    // Capture Landing screenshot
    const shotLanding = await send('Page.captureScreenshot', { format: 'png' });
    if (shotLanding && shotLanding.data) {
      fs.writeFileSync('hero_verified.png', Buffer.from(shotLanding.data, 'base64'));
      console.log('Landing screenshot saved to hero_verified.png!');
    }

    // Click "Growth Dashboard" button in navbar
    await send('Runtime.evaluate', {
      expression: `
        const btn = Array.from(document.querySelectorAll('button')).find(b => b.textContent.includes('Dashboard'));
        if (btn) btn.click();
      `
    });

    await new Promise(r => setTimeout(r, 1000));

    // Capture Dashboard screenshot
    const shotDash = await send('Page.captureScreenshot', { format: 'png' });
    if (shotDash && shotDash.data) {
      fs.writeFileSync('dashboard_verified.png', Buffer.from(shotDash.data, 'base64'));
      console.log('Dashboard screenshot saved to dashboard_verified.png!');
    }

    ws.close();
  } catch(e) {
    console.error('Test error:', e);
  } finally {
    edge.kill();
  }
}

testScreenshots();
