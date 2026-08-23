// jarvis_baileys.js — reliable WhatsApp for J.A.R.V.I.S. (Baileys, no Chromium).
// Robust multi-file auth survives restarts/reboots; auto-reconnects.
// HTTP: POST /send {number|name, message}  ·  GET /status
// Inbound:
//   - BOSS's own message "jarvis <command>" (any direct chat, incl. Message
//     Yourself) → forwarded to the PC Jarvis command bridge (127.0.0.1:8760)
//     for REAL tool execution; the spoken reply comes back on WhatsApp.
//   - Anyone else's "jarvis ..." → mission-aware Hermes chat (NO execution).
// First run: scan the QR shown in this window (WhatsApp > Linked Devices).
const dns = require('dns');
try { dns.setDefaultResultOrder('ipv4first'); } catch(e) {}
const http = require('http');
const fs = require('fs');
const qrcode = require('qrcode-terminal');
const pino = require('pino');
const { default: makeWASocket, useMultiFileAuthState, DisconnectReason, downloadMediaMessage, Browsers, fetchLatestBaileysVersion } = require('@whiskeysockets/baileys');

const AUTH_DIR = 'E:\\jarvis\\wa\\auth';
const PORT = 3200;
let sock = null, ready = false;

// Mirror all logs to wa/baileys.log so inbound decisions are debuggable.
const LOG_FILE = 'E:\\jarvis\\wa\\baileys.log';
const _clog = console.log.bind(console);
console.log = (...a) => {
  _clog(...a);
  try { fs.appendFileSync(LOG_FILE, new Date().toISOString() + ' ' + a.join(' ') + '\n'); } catch {}
};

// Forward a Boss command to the PC Jarvis GUI (command bridge on 8760) for
// REAL execution with all 100+ tools. Resolves true if Jarvis accepted it.
function bridgePost(path, payload, timeoutMs) {
  return new Promise((resolve) => {
    const body = JSON.stringify(payload);
    const req = http.request({
      hostname: '127.0.0.1', port: 8760, path, method: 'POST',
      headers: { 'Content-Type': 'application/json', 'Content-Length': Buffer.byteLength(body) },
    }, (r) => { let d = ''; r.on('data', c => d += c); r.on('end', () => {
      try { resolve(JSON.parse(d)); } catch { resolve({ ok: false }); }
    }); });
    req.on('error', () => resolve({ ok: false }));
    req.setTimeout(timeoutMs || 4000, () => { try { req.destroy(); } catch {} resolve({ ok: false }); });
    req.write(body); req.end();
  });
}
function sendToJarvis(text, replyTo) {
  return bridgePost('/command', {
    text,
    reply_to: replyTo,
    owner_id: replyTo || 'boss',
    source: 'whatsapp-owner'
  }, 10000);
}

async function askJarvisChat(prompt, ownerId) {
  const response = await bridgePost('/chat', {
    text: String(prompt || '').slice(0, 2000),
    owner_id: ownerId || 'public-chat',
    source: 'whatsapp-chat'
  }, 180000);
  return response && response.ok && response.text
    ? response.text
    : 'JARVIS PC intelligence is temporarily unreachable. No command was executed.';
}

const publicChatWindows = new Map();
function allowPublicChat(jid) {
  const now = Date.now();
  const recent = (publicChatWindows.get(jid) || []).filter(stamp => now - stamp < 15 * 60 * 1000);
  if (recent.length >= 5) return false;
  recent.push(now);
  publicChatWindows.set(jid, recent);
  return true;
}

let isReconnecting = false;

async function start() {
  if (isReconnecting) return;
  isReconnecting = true;

  try {
    if (sock) {
      try { sock.ev.removeAllListeners(); } catch {}
    }
    let version = [2, 3000, 1043857760];

    const { state, saveCreds } = await useMultiFileAuthState(AUTH_DIR);
    sock = makeWASocket({ 
      version,
      auth: state, 
      logger: pino({ level: 'silent' }), 
      browser: Browsers.windows('Desktop'),
      syncFullHistory: false,
      connectTimeoutMs: 60000,
      defaultQueryTimeoutMs: 60000,
      keepAliveIntervalMs: 15000
    });
    sock.ev.on('creds.update', saveCreds);
    sock.ev.on('connection.update', async (u) => {
      const { connection, lastDisconnect, qr } = u;
      if (qr) { 
        console.log('\n[JARVIS Baileys] Scan this QR Code from WhatsApp:\n'); 
        qrcode.generate(qr, { small: true }); 
        try {
          const QRCodeLib = require('qrcode');
          const qrPath = 'C:\\Users\\HP\\.gemini\\antigravity\\brain\\d4843218-84b8-421a-ab9e-2517e70e2dd2\\qr.png';
          await QRCodeLib.toFile(qrPath, qr, { width: 1000, margin: 4, errorCorrectionLevel: 'H' });
          const htmlPath = 'C:\\Users\\HP\\.gemini\\antigravity\\brain\\d4843218-84b8-421a-ab9e-2517e70e2dd2\\qr.html';
          const base64Data = await QRCodeLib.toDataURL(qr, { width: 1000, margin: 4, errorCorrectionLevel: 'H' });
          const htmlContent = `<!DOCTYPE html><html><head><meta charset="utf-8"><title>JARVIS WhatsApp Live QR Code</title><meta http-equiv="refresh" content="3"></head><body style="background:#04080f;color:#fff;font-family:sans-serif;display:flex;flex-direction:column;align-items:center;justify-content:center;height:100vh;margin:0;"><h1 style="color:#00e5ff;margin-bottom:10px;">⚡ J.A.R.V.I.S. WhatsApp Live QR Code</h1><p style="color:#00ff88;font-size:18px;margin-bottom:20px;">Open WhatsApp > Linked Devices > Link a Device & Scan Below</p><div style="background:#fff;padding:24px;border-radius:20px;box-shadow:0 0 50px rgba(0,229,255,0.6);"><img src="${base64Data}" style="width:420px;height:420px;display:block;"></div></body></html>`;
          fs.writeFileSync(htmlPath, htmlContent);
          console.log('[JARVIS Baileys] Saved HD 1000px QR image & HTML artifact.');
        } catch (e) { console.error('[JARVIS Baileys] QR save error:', e); }
      }
      if (connection === 'open') { 
        ready = true; 
        isReconnecting = false;
        console.log('[JARVIS Baileys] READY — connected & permanent.'); 
      }
      if (connection === 'close') {
        ready = false;
        const code = lastDisconnect && lastDisconnect.error && lastDisconnect.error.output && lastDisconnect.error.output.statusCode;
        console.log(`[JARVIS Baileys] Disconnected with code: ${code}`);
        if (code === DisconnectReason.loggedOut) {
          console.log(`[JARVIS Baileys] Explicit logout detected. Purging auth directory...`);
          try { fs.rmSync(AUTH_DIR, { recursive: true, force: true }); } catch {}
        }
        setTimeout(() => {
          isReconnecting = false;
          start();
        }, 2000);
      }
    });
  // Inbound "jarvis ..." — Boss's own messages get REAL execution on the PC;
  // everyone else gets mission-aware chat only (no execution — security).
  sock.ev.on('messages.upsert', async (m) => {
    try {
      const msg = m.messages[0];
      if (!msg || !msg.message) return;

      // --- VOICE COMMANDS: a voice note the Boss sends to HIMSELF (Message
      // Yourself chat) is a Jarvis command — download, let the PC transcribe
      // with Gemini, execute, and reply here.
      const selfJid = sock.user && sock.user.id ? sock.user.id.split(':')[0] + '@s.whatsapp.net' : '';
      if (msg.key.fromMe && msg.message.audioMessage && msg.key.remoteJid === selfJid) {
        try {
          console.log('[Inbound] VOICE command in self-chat — downloading...');
          const buf = await downloadMediaMessage(msg, 'buffer', {});
          const p = 'E:\\jarvis\\scratch\\wa_voice_' + Date.now() + '.ogg';
          fs.writeFileSync(p, buf);
          const ownerNumber = selfJid.split('@')[0];
          const res = await bridgePost('/voice', {
            path: p,
            reply_to: ownerNumber,
            owner_id: ownerNumber,
            source: 'whatsapp-owner-voice'
          }, 60000);
          if (res.ok) {
            await sock.sendMessage(msg.key.remoteJid, { text: '🤖 Suna, Boss — executing: "' + (res.transcript || 'voice command') + '"' });
          } else {
            await sock.sendMessage(msg.key.remoteJid, { text: '🤖 Voice note mili magar samajh nahi saka (' + (res.error || 'PC Jarvis unreachable') + ').' });
          }
        } catch (e) { console.log('[Inbound] voice handling error: ' + String(e).slice(0, 120)); }
        return;
      }

      const text = (msg.message.conversation || (msg.message.extendedTextMessage && msg.message.extendedTextMessage.text) || '').trim();
      if (!text.toLowerCase().startsWith('jarvis')) return;
      const cmd = text.replace(/^jarvis[,:\s]*/i, '').trim() || 'hello';
      const jid = msg.key.remoteJid || '';
      console.log('[Inbound] fromMe=' + !!msg.key.fromMe + ' jid=' + jid + ' cmd=' + cmd.slice(0, 60));

      if (msg.key.fromMe && jid.endsWith('@s.whatsapp.net')) {
        // The Boss himself (incl. "Message Yourself") → execute on the PC.
        const number = jid.split('@')[0];
        const result = await sendToJarvis(cmd, number);
        if (result && result.ok) {
          await sock.sendMessage(jid, { text: '🤖 On it, Boss — executing: ' + cmd });
        } else {
          const hasDecision = !!(result && result.message);
          const reply = hasDecision ? result.message : await askJarvisChat(cmd, number);
          const suffix = hasDecision ? '' : '\n\n(PC Jarvis unreachable — chat-only reply, nothing executed.)';
          await sock.sendMessage(jid, { text: reply + suffix });
        }
      } else if (!msg.key.fromMe) {
        // Someone else → chat reply only, never execute.
        if (!allowPublicChat(jid)) {
          await sock.sendMessage(jid, { text: 'JARVIS public chat limit reached. Please try again later.' });
          return;
        }
        const reply = await askJarvisChat(cmd, 'public:' + jid);
        await sock.sendMessage(jid, { text: reply });
      }
    } catch {}
  });
  } catch (e) {
    console.error('[JARVIS Baileys] start error:', e);
    isReconnecting = false;
  }
}
start();

function lookupContactNumber(nameOrNum) {
  if (!nameOrNum) return '';
  let digits = String(nameOrNum).replace(/[^0-9]/g, '');
  if (digits && digits.length >= 10) return digits;

  try {
    const fs = require('fs');
    const path = require('path');
    const cfgPath = path.resolve(__dirname, '../config/wa_contacts.json');
    if (fs.existsSync(cfgPath)) {
      const data = JSON.parse(fs.readFileSync(cfgPath, 'utf8'));
      const contacts = data.contacts || {};
      const cleanTarget = String(nameOrNum).toLowerCase().replace(/\b(contact|number|bhai|sahab|sb|ji|ka|ko)\b/g, '').trim();

      for (const [key, num] of Object.entries(contacts)) {
        const cleanKey = key.toLowerCase().replace(/\b(contact|number|bhai|sahab|sb|ji|ka|ko)\b/g, '').trim();
        if (cleanTarget && (cleanKey === cleanTarget || cleanKey.includes(cleanTarget) || cleanTarget.includes(cleanKey))) {
          const matchedDigits = String(num).replace(/[^0-9]/g, '');
          if (matchedDigits.length >= 10) return matchedDigits;
        }
      }
    }
  } catch (e) {
    console.error('[Baileys] Error reading wa_contacts.json:', e);
  }
  return '';
}

async function sendTo(numberOrName, text) {
  let digits = lookupContactNumber(numberOrName);
  if (!digits) throw new Error('Baileys needs a valid number or saved contact name');
  await sock.sendMessage(digits + '@s.whatsapp.net', { text });
}

async function sendAudioTo(numberOrName, audioPath) {
  let digits = lookupContactNumber(numberOrName);
  if (!digits) throw new Error('Baileys needs a valid number or saved contact name');
  if (!fs.existsSync(audioPath)) throw new Error(`Audio file not found at ${audioPath}`);

  const { execSync } = require('child_process');
  let finalPath = audioPath;

  if (!audioPath.endsWith('.ogg')) {
    const oggPath = audioPath.replace(/\.[^.]+$/, '') + '_wa.ogg';
    try {
      execSync(`ffmpeg -y -i "${audioPath}" -c:a libopus -b:a 32k "${oggPath}"`, { stdio: 'ignore' });
      if (fs.existsSync(oggPath)) {
        finalPath = oggPath;
      }
    } catch (e) {
      console.error('[Baileys] FFmpeg conversion warning:', e);
    }
  }

  const buffer = fs.readFileSync(finalPath);
  await sock.sendMessage(digits + '@s.whatsapp.net', {
    audio: buffer,
    mimetype: 'audio/ogg; codecs=opus',
    ptt: true
  });
}

http.createServer((req, res) => {
  if (req.method === 'POST' && (req.url === '/send' || req.url === '/send_audio')) {
    let b = ''; req.on('data', d => b += d); req.on('end', async () => {
      try {
        const { number, name, message, audioPath } = JSON.parse(b || '{}');
        if (!ready) { res.writeHead(503); return res.end(JSON.stringify({ ok: false, error: 'not ready' })); }
        if (audioPath) {
          await sendAudioTo(number || name, audioPath);
          if (message) { await sendTo(number || name, message); }
        } else {
          await sendTo(number || name, message);
        }
        res.writeHead(200); res.end(JSON.stringify({ ok: true }));
      } catch (e) { res.writeHead(500); res.end(JSON.stringify({ ok: false, error: String(e).slice(0, 150) })); }
    });
  } else if (req.url === '/status') { res.writeHead(200); res.end(JSON.stringify({ ready })); }
  else if (req.url.startsWith('/pair-code')) {
    const urlObj = new URL(req.url, 'http://127.0.0.1:3200');
    const phone = urlObj.searchParams.get('phone') || '923468053268';
    try {
      const cleanPhone = String(phone).replace(/[^0-9]/g, '');
      sock.requestPairingCode(cleanPhone).then(code => {
        console.log(`\n🔑 [CUSTOM PAIRING CODE for ${cleanPhone}]: ${code}\n`);
        res.writeHead(200, { 'Content-Type': 'application/json' });
        res.end(JSON.stringify({ ok: true, phone: cleanPhone, code }));
      }).catch(e => {
        res.writeHead(500, { 'Content-Type': 'application/json' });
        res.end(JSON.stringify({ ok: false, error: String(e) }));
      });
    } catch (err) {
      res.writeHead(500, { 'Content-Type': 'application/json' });
      res.end(JSON.stringify({ ok: false, error: String(err) }));
    }
  }
  else if (req.url === '/reset-session') {
    try {
      ready = false;
      try { fs.rmSync(AUTH_DIR, { recursive: true, force: true }); } catch {}
      res.writeHead(200, { 'Content-Type': 'application/json' });
      res.end(JSON.stringify({ ok: true, message: 'Auth session reset. Restarting Baileys...' }));
      setTimeout(() => { start(); }, 1000);
    } catch (err) {
    }
  }
  else if (req.url === '/qr' || req.url === '/qr.png') {
    const qrImgPath = 'C:\\Users\\HP\\.gemini\\antigravity\\brain\\d4843218-84b8-421a-ab9e-2517e70e2dd2\\qr.png';
    if (fs.existsSync(qrImgPath)) {
      res.writeHead(200, { 'Content-Type': 'image/png' });
      res.end(fs.readFileSync(qrImgPath));
    } else {
      res.writeHead(404); res.end('QR image not ready yet');
    }
  }
  else if (req.url === '/' || req.url === '') {
    res.writeHead(200, { 'Content-Type': 'text/html; charset=utf-8' });
    res.end('<html><body style="background:#04080f;color:#19e0ff;font-family:Consolas,monospace;padding:30px">' +
      '<h2>🤖 J.A.R.V.I.S. — WhatsApp Bridge (Baileys)</h2>' +
      '<p>Status: <b style="color:' + (ready ? '#2f6' : '#f55') + '">' + (ready ? 'ONLINE — WhatsApp linked & ready' : 'CONNECTING…') + '</b></p>' +
      '<p>API: POST /send {number|name, message, audioPath} &middot; GET /status</p>' +
      '<p>Commands: message yourself "jarvis &lt;command&gt;" or send a VOICE note to yourself.</p>' +
      '</body></html>');
  }
  else { res.writeHead(404); res.end('jarvis-baileys'); }
}).listen(PORT, '127.0.0.1', () => console.log('[JARVIS Baileys] private HTTP on http://127.0.0.1:' + PORT));
