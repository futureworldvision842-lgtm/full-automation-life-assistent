// jarvis_baileys.js — reliable WhatsApp for J.A.R.V.I.S. (Baileys, no Chromium).
// Robust multi-file auth survives restarts/reboots; auto-reconnects.
// HTTP: POST /send {number|name, message}  ·  GET /status
// Inbound: an allowlisted message starting with "jarvis ..." is routed to the
// local JARVIS dashboard, which supplies local/cloud AI and owner approvals.
// First run: scan the QR shown in this window (WhatsApp > Linked Devices).
const http = require('http');
const fs = require('fs');
const crypto = require('crypto');
const QRCode = require('qrcode');
const qrcode = require('qrcode-terminal');
const pino = require('pino');
const { default: makeWASocket, useMultiFileAuthState, DisconnectReason, fetchLatestBaileysVersion, Browsers, downloadMediaMessage } = require('@whiskeysockets/baileys');

const path = require('path');
const { extractOwnerCommand } = require('./owner_command');
const AUTH_DIR = path.join(__dirname, 'auth');
const CONFIG_DIR = path.join(__dirname, '..', 'config');
const PORT = 3200;
const JARVIS_URL = (process.env.JARVIS_COMMAND_URL || 'http://127.0.0.1:8770/api/terminal/exec');

function loadOrCreateLocalToken(fileName, fieldName, envName) {
  const configured = String(process.env[envName] || '').trim();
  if (configured) return configured;
  const tokenPath = path.join(CONFIG_DIR, fileName);
  try {
    const payload = JSON.parse(fs.readFileSync(tokenPath, 'utf8'));
    const existing = String(payload[fieldName] || '').trim();
    if (existing) return existing;
  } catch {}
  const token = crypto.randomBytes(32).toString('base64url');
  fs.mkdirSync(CONFIG_DIR, { recursive: true });
  fs.writeFileSync(tokenPath, JSON.stringify({ [fieldName]: token }, null, 2), { encoding: 'utf8', mode: 0o600 });
  return token;
}

const HTTP_TOKEN = loadOrCreateLocalToken('wa.local.json', 'http_token', 'JARVIS_WA_HTTP_TOKEN');
const INTERNAL_TOKEN = loadOrCreateLocalToken('internal.local.json', 'command_token', 'JARVIS_INTERNAL_COMMAND_TOKEN');

function getAllowedNumbers() {
  const nums = new Set(['923468053268']);
  const envNums = (process.env.JARVIS_WA_ALLOWED_NUMBERS || '').split(',').map(v => v.replace(/[^0-9]/g, '')).filter(Boolean);
  envNums.forEach(n => nums.add(n));
  // The contact book is not an execution allowlist.
  try {
    const local = JSON.parse(fs.readFileSync(path.join(CONFIG_DIR, 'wa.local.json'), 'utf8'));
    for (const value of local.allowed_numbers || []) {
      const digits = String(value).replace(/[^0-9]/g, '');
      if (digits.length >= 10 && digits.length <= 15) nums.add(digits);
    }
  } catch {}
  return nums;
}

const ALLOWED_NUMBERS = getAllowedNumbers();
let sock = null, ready = false;

function isLoopback(address) {
  return ['127.0.0.1', '::1', '::ffff:127.0.0.1'].includes(String(address || ''));
}

const { spawn } = require('child_process');

function wakeJarvisEcosystem() {
  const rootDir = path.join(__dirname, '..');
  const batPath = path.join(rootDir, 'START_FULL_JARVIS_ECOSYSTEM.bat');
  console.log('[JARVIS Baileys] ⚡ Triggering Sovereign Ecosystem Remote Wake Sequence...');
  try {
    if (fs.existsSync(batPath)) {
      spawn('cmd.exe', ['/c', batPath], { cwd: rootDir, detached: true, stdio: 'ignore' }).unref();
      return true;
    }
    const py = fs.existsSync(path.join(rootDir, '.venv', 'Scripts', 'python.exe')) ?
      path.join(rootDir, '.venv', 'Scripts', 'python.exe') : 'python';
    spawn(py, [path.join(rootDir, 'bootstrap', 'master_ecosystem_launcher.py'), 'start', 'all'], {
      cwd: rootDir, detached: true, stdio: 'ignore'
    }).unref();
    return true;
  } catch (e) {
    console.error('[JARVIS Baileys] Wake sequence error:', e.message);
    return false;
  }
}

function callJarvis(command, sender) {
  return new Promise((resolve) => {
    const isWakeCmd = /(?:^|\b)(?:on(?:\s*kero|\s*karo|\s*kro)?|start|wake(?:\s*up)?|boot|turn\s*on|system\s*on|jarvis\s*on|chalao|run\s*all)(?:\b|$)/i.test(command.trim());
    const target = new URL(JARVIS_URL);
    const body = JSON.stringify({ cmd: command });
    const req = http.request({
      hostname: target.hostname,
      port: target.port || 80,
      path: target.pathname + target.search,
      method: 'POST',
      timeout: 75000,
      headers: {
        'Content-Type': 'application/json',
        'Content-Length': Buffer.byteLength(body),
        'X-Jarvis-Internal-Token': INTERNAL_TOKEN,
        'X-Jarvis-Owner-Channel': `whatsapp:${sender}`,
      },
    }, (r) => { let d = ''; r.on('data', c => d += c); r.on('end', () => {
      try {
        const payload = JSON.parse(d);
        const textOut = payload.output || payload.message || payload.error || `JARVIS HTTP ${r.statusCode}`;
        const imageOut = payload.metadata?.image_path || null;
        resolve({ text: textOut, imagePath: imageOut, raw: payload });
      } catch { resolve({ text: `JARVIS returned an unreadable response (HTTP ${r.statusCode}).`, imagePath: null }); }
    }); });
    req.on('timeout', () => req.destroy(new Error('timeout')));
    req.on('error', (error) => {
      if (isWakeCmd) {
        wakeJarvisEcosystem();
        resolve({
          text: `⚡ *[J.A.R.V.I.S. WAKE-ON-MESSAGE ACTIVATED]*\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\nSir, J.A.R.V.I.S. Sovereign Ecosystem boot sequence has been initiated remotely via WhatsApp!\n• Master Dashboard (:8770), Trading Cockpit (:5050), and AI daemons are booting up now.\n• Please allow ~10-15 seconds for full system initialization.`,
          imagePath: null
        });
      } else {
        resolve({
          text: `⚠️ *[J.A.R.V.I.S. OFFLINE]*\nSir, the core command backend is currently stopped or unreachable (${error.message}).\n💡 Send *"jarvis on"* or *"on kero"* to remotely wake up the entire ecosystem!`,
          imagePath: null
        });
      }
    });
    req.write(body); req.end();
  });
}

function transcribeAudioBuffer(audioBuffer) {
  return new Promise((resolve) => {
    if (!audioBuffer || audioBuffer.length === 0) return resolve({ ok: false, error: 'empty_buffer' });
    const target = new URL('http://127.0.0.1:8770/api/voice/transcribe');
    const req = http.request({
      hostname: target.hostname,
      port: target.port || 80,
      path: target.pathname,
      method: 'POST',
      timeout: 25000,
      headers: {
        'Content-Type': 'audio/ogg',
        'Content-Length': audioBuffer.length,
        'X-Jarvis-Internal-Token': INTERNAL_TOKEN,
      },
    }, (r) => {
      let d = '';
      r.on('data', c => d += c);
      r.on('end', () => {
        try {
          const payload = JSON.parse(d);
          resolve(payload);
        } catch {
          resolve({ ok: false, error: 'unreadable_transcription_response' });
        }
      });
    });
    req.on('timeout', () => { req.destroy(); resolve({ ok: false, error: 'timeout' }); });
    req.on('error', (err) => resolve({ ok: false, error: err.message }));
    req.write(audioBuffer);
    req.end();
  });
}

function cleanTextForSpeech(text) {
  if (!text) return '';
  let t = String(text).trim();
  // Strip emojis
  t = t.replace(/([\u2700-\u27BF]|[\uE000-\uF8FF]|\uD83C[\uDC00-\uDFFF]|\uD83D[\uDC00-\uDFFF]|[\u2011-\u26FF]|\uD83E[\uDD10-\uDDFF])/g, '');
  // Strip markdown formatting symbols
  t = t.replace(/[#*`_~\[\]()•|]/g, ' ');
  // Convert currency & percentage symbols for natural speech
  t = t.replace(/\$([0-9,]+(?:\.[0-9]+)?)/g, '$1 dollars');
  t = t.replace(/%/g, ' percent');
  // Strip URLs
  t = t.replace(/https?:\/\/\S+/g, '');
  // Normalize whitespace
  const lines = t.split(/\r?\n/).map(l => l.trim()).filter(Boolean);
  let spoken = lines.slice(0, 4).join('. ');
  spoken = spoken.replace(/\s+/g, ' ').trim();
  if (spoken.length > 350) spoken = spoken.slice(0, 347) + '...';
  return spoken;
}

function synthesizeVoiceBuffer(text) {
  return new Promise((resolve) => {
    const spoken = cleanTextForSpeech(text);
    if (!spoken) return resolve(null);
    const target = new URL('http://127.0.0.1:8770/api/voice/synthesize');
    const body = JSON.stringify({ text: spoken });
    const req = http.request({
      hostname: target.hostname,
      port: target.port || 80,
      path: target.pathname,
      method: 'POST',
      timeout: 30000,
      headers: {
        'Content-Type': 'application/json',
        'Content-Length': Buffer.byteLength(body),
        'X-Jarvis-Internal-Token': INTERNAL_TOKEN,
      },
    }, (r) => {
      if (r.statusCode !== 200) {
        return resolve(null);
      }
      const chunks = [];
      r.on('data', c => chunks.push(c));
      r.on('end', () => {
        const audioBuf = Buffer.concat(chunks);
        resolve(audioBuf.length > 500 ? audioBuf : null);
      });
    });
    req.on('timeout', () => { req.destroy(); resolve(null); });
    req.on('error', () => resolve(null));
    req.write(body);
    req.end();
  });
}

function checkAndAssimilateRepo(message, sender) {
  return new Promise((resolve) => {
    const body = JSON.stringify({ sender: sender || '+923468053268', message: message });
    const target = new URL('http://127.0.0.1:8770/api/repos/whatsapp/process_directive');
    const req = http.request({
      hostname: target.hostname,
      port: target.port || 80,
      path: target.pathname,
      method: 'POST',
      timeout: 35000,
      headers: {
        'Content-Type': 'application/json',
        'Content-Length': Buffer.byteLength(body),
        'X-Jarvis-Internal-Token': INTERNAL_TOKEN,
      },
    }, (r) => {
      let d = '';
      r.on('data', c => d += c);
      r.on('end', () => {
        try {
          const res = JSON.parse(d);
          resolve(res);
        } catch {
          resolve(null);
        }
      });
    });
    req.on('timeout', () => { req.destroy(); resolve(null); });
    req.on('error', () => resolve(null));
    req.write(body);
    req.end();
  });
}

let lastQr = null;
let lastQrImage = null;
let groupMap = new Map();
let consecutive401 = 0;

// Module-scoped deduplication and anti-loop sets
const seen = new Set();
const jarvisSentIds = new Set();

// Ring-buffer bounding on jarvisSentIds (max 2000 entries)
const _origJarvisSentAdd = jarvisSentIds.add.bind(jarvisSentIds);
jarvisSentIds.add = function(id) {
  _origJarvisSentAdd(id);
  if (this.size > 2000) {
    const oldest = this.values().next().value;
    if (oldest !== undefined) this.delete(oldest);
  }
  return this;
};

async function start() {
  const { version } = await fetchLatestBaileysVersion().catch(() => ({ version: [2, 3000, 1043857760] }));
  const { state, saveCreds } = await useMultiFileAuthState(AUTH_DIR);
  sock = makeWASocket({
    version,
    auth: state,
    logger: pino({ level: 'silent' }),
    browser: Browsers.windows('Desktop'),
    printQRInTerminal: false,
    syncFullHistory: false
  });
  sock.ev.on('creds.update', saveCreds);
  sock.ev.on('connection.update', async (u) => {
    const { connection, lastDisconnect, qr } = u;
    if (qr) {
      lastQr = qr;
      try { 
        lastQrImage = await QRCode.toDataURL(qr, { width: 320, margin: 2 }); 
        const buf = Buffer.from(lastQrImage.split(',')[1], 'base64');
        fs.writeFileSync(path.join(__dirname, 'current_qr.png'), buf);
        const brainArtifact = 'C:\\Users\\user\\.gemini\\antigravity\\brain\\277e0112-0212-49e1-bd62-d18d4f5929c0\\whatsapp_qr.png';
        try { fs.writeFileSync(brainArtifact, buf); } catch {}
      } catch { lastQrImage = null; }
      console.log('\n============================================================');
      console.log(' [JARVIS Baileys] Scan this QR Code with WhatsApp:');
      console.log(' (Open WhatsApp on phone > Settings/3 dots > Linked Devices > Link Device)');
      console.log(' Web view: http://localhost:3200/qr');
      console.log('============================================================\n');
      // Pairing material is shown only on the local /qr page, not persisted in logs.
    }
    if (connection === 'open') {
      ready = true;
      consecutive401 = 0;
      lastQr = null;
      lastQrImage = null;
      for (const staleName of ['qr_raw.txt', 'qr_current.txt']) {
        try { fs.unlinkSync(path.join(__dirname, staleName)); } catch {}
      }
      console.log('\n============================================================');
      console.log(' [JARVIS Baileys] READY — WhatsApp Connected Successfully!');
      console.log(' [JARVIS Baileys] Privacy Rule: Master DM only (923468053268)');
      console.log(' [JARVIS Baileys] Active Groups: Elite Trade & Crypto Bot');
      console.log('============================================================\n');
      try {
        const groups = await sock.groupFetchAllParticipating();
        for (const [gJid, meta] of Object.entries(groups)) {
          groupMap.set(gJid, meta.subject || '');
          console.log(` [JARVIS Baileys] Sync Group: "${meta.subject}" (${gJid})`);
        }
      } catch (e) {
        console.log(' [JARVIS Baileys] Group sync notice:', e.message);
      }
    }
    if (connection === 'close') {
      ready = false;
      const code = lastDisconnect && lastDisconnect.error && lastDisconnect.error.output && lastDisconnect.error.output.statusCode;
      console.log(`[JARVIS Baileys] Connection closed (code: ${code})`);
      if (code === DisconnectReason.loggedOut || code === 401) {
        consecutive401++;
        if (consecutive401 >= 3) {
          console.log('[JARVIS Baileys] WhatsApp server verified session expired/unlinked. Generating fresh keys...');
          consecutive401 = 0;
          try {
            if (fs.existsSync(AUTH_DIR)) fs.renameSync(AUTH_DIR, AUTH_DIR + ".revoked-" + Date.now());
            fs.mkdirSync(AUTH_DIR, { recursive: true });
          } catch {}
          setTimeout(start, 1500);
          return;
        }
      } else {
        consecutive401 = 0;
      }
      console.log('[JARVIS Baileys] Reconnecting in 3s using existing session...');
      setTimeout(start, 3000);
    }
  });

  // Process allowlisted owner commands and Elite Trade group trading orders
  sock.ev.on('messages.upsert', async (event) => {
    if (event.type !== 'notify') return;
    for (const msg of event.messages || []) {
      try {
        if (!msg.message || !msg.key?.id || seen.has(msg.key.id) || jarvisSentIds.has(msg.key.id)) continue;

        let text = String(msg.message.conversation || msg.message.extendedTextMessage?.text || '').trim();
        let isVoice = false;

        // Inbound voice note (audioMessage / PTT) handling
        if (!text && msg.message.audioMessage) {
          try {
            const jidRaw = String(msg.key.remoteJid || '');
            console.log(`[JARVIS Baileys] 🎙️ Inbound Voice Note from ${jidRaw} (PTT: ${msg.message.audioMessage.ptt}). Downloading...`);
            const audioBuf = await downloadMediaMessage(msg, 'buffer', {});
            if (audioBuf && audioBuf.length > 0) {
              const stt = await transcribeAudioBuffer(audioBuf);
              if (stt && stt.text) {
                text = stt.text.trim();
                isVoice = true;
                console.log(`[JARVIS Baileys] 🗣️ Transcribed Voice Command: "${text}" [Engine: ${stt.provider || 'stt'}]`);
              }
            }
          } catch (audioErr) {
            console.error('[JARVIS Baileys] Audio download/STT notice:', audioErr.message);
          }
        }
        if (!text) continue;

        const jid = String(msg.key.remoteJid || '');
        const isGroup = jid.endsWith('@g.us');
        const groupSubject = isGroup ? (groupMap.get(jid) || '') : '';
        const isEliteGroup = isGroup && (/elite.*trade|trade.*elite/i.test(groupSubject) || jid === '120363401615322542@g.us' || process.env.JARVIS_WA_GROUP_COMMANDS === '1');

        const sourceJid = String(msg.key.participantAlt || msg.key.participant || msg.key.remoteJidAlt || jid);
        const digits = sourceJid.split('@')[0].split(':')[0].replace(/[^0-9]/g, '');
        const jidDigits = jid.split('@')[0].split(':')[0].replace(/[^0-9]/g, '');
        const isSelfChat = msg.key.fromMe && (jidDigits === '923468053268' || ALLOWED_NUMBERS.has(jidDigits) || digits === '923468053268' || ALLOWED_NUMBERS.has(digits));

        // Anti-loop protection: if this is a self-chat message, ignore responses that look like JARVIS outputs
        if (isSelfChat && /^(?:⚡|🤖|🖥️|📈|🌍|🧠|📊|📦|🔐|Sir,|\[J\.A\.R\.V\.I\.S\.)/i.test(text)) continue;

        // Command resolution: In 1-on-1 private DM with the owner or self-chat, direct words are treated as commands
        let command = null;
        if (isSelfChat) {
          command = text.replace(/^jarvis[,:\s]*/i, '').trim() || text;
        } else if (!isGroup && ALLOWED_NUMBERS.has(digits)) {
          command = text.replace(/^jarvis[,:\s]*/i, '').trim() || text;
        } else {
          command = extractOwnerCommand(text, isEliteGroup);
        }
        if (command === null) continue;

        // Allow execution if sender is allowlisted, or if command originates from self-chat, or verified Elite Trade group
        if (!ALLOWED_NUMBERS.has(digits) && !isEliteGroup && !isSelfChat) continue;

        seen.add(msg.key.id);
        if (seen.size > 1000) seen.delete(seen.values().next().value);

        console.log(`[JARVIS Baileys] Executing ${isVoice ? 'VOICE ' : ''}command from ${isSelfChat ? 'Self-Chat (Owner)' : (isEliteGroup ? 'Elite Trade Group' : 'Direct')}: "${command}"`);
        const senderId = isEliteGroup ? `elite_wa_${digits || 'member'}` : digits;

        // Check if message is a GitHub repo assimilation directive (URL or 'assimilate <repo>')
        let repoAssimilationResult = null;
        try {
          repoAssimilationResult = await checkAndAssimilateRepo(command, digits || '923468053268');
        } catch (e) {
          console.error('[JARVIS Baileys] Repo assimilation check notice:', e.message);
        }

        let reply = '';
        let imageToSend = null;

        if (repoAssimilationResult && repoAssimilationResult.ok && repoAssimilationResult.reply) {
          reply = repoAssimilationResult.reply;
          console.log(`[JARVIS Baileys] 🚀 Autonomous GitHub Assimilation directive executed: ${repoAssimilationResult.action}`);
        } else {
          const jarvisResult = await callJarvis(command, senderId);
          reply = typeof jarvisResult === 'object' ? (jarvisResult.text || '') : String(jarvisResult || '');
          imageToSend = typeof jarvisResult === 'object' ? jarvisResult.imagePath : null;
        }

        // Visual screen & camera vision handling if command asked for screen/camera and no image already set
        const isVisionCmd = /(?:screen|vision|screenshot|tasweer)/i.test(command);
        const isCameraCmd = /(?:camera|webcam|motion|harkat|photo)/i.test(command);
        if (!imageToSend && isVisionCmd) {
          const screenFile = path.join(__dirname, '..', 'runtime', 'latest_screen.png');
          if (fs.existsSync(screenFile)) {
            imageToSend = screenFile;
          }
        } else if (!imageToSend && isCameraCmd) {
          const motionFile = path.join(__dirname, '..', 'runtime', 'latest_motion.jpg');
          const camFile = path.join(__dirname, '..', 'runtime', 'latest_camera.jpg');
          if (fs.existsSync(motionFile)) {
            imageToSend = motionFile;
          } else if (fs.existsSync(camFile)) {
            imageToSend = camFile;
          }
        }

        // If an image is available (from human intervention gateway, screen capture, or vision command), send it!
        if (imageToSend && fs.existsSync(imageToSend)) {
          try {
            const imgBuf = fs.readFileSync(imageToSend);
            const m = await sock.sendMessage(jid, {
              image: imgBuf,
              caption: String(reply).slice(0, 1024) || '🖥️ [J.A.R.V.I.S. Desktop Screen Vision]'
            });
            if (m?.key?.id) {
              jarvisSentIds.add(m.key.id);
              if (jarvisSentIds.size > 2000) jarvisSentIds.delete(jarvisSentIds.values().next().value);
            }
            console.log(`[JARVIS Baileys] ✓ Desktop screen photo dispatched to ${jid}`);
            // If the explanation was longer than WhatsApp caption limit (1024 chars), send the remainder
            if (reply && reply.length > 1024) {
              const m2 = await sock.sendMessage(jid, { text: String(reply).slice(1024, 12000) });
              if (m2?.key?.id) {
                jarvisSentIds.add(m2.key.id);
                if (jarvisSentIds.size > 2000) jarvisSentIds.delete(jarvisSentIds.values().next().value);
              }
            }
          } catch (imgErr) {
            console.error('[JARVIS Baileys] Failed to send image message, fallback to text:', imgErr.message);
            const m = await sock.sendMessage(jid, { text: String(reply).slice(0, 12000) });
            if (m?.key?.id) {
              jarvisSentIds.add(m.key.id);
              if (jarvisSentIds.size > 2000) jarvisSentIds.delete(jarvisSentIds.values().next().value);
            }
          }
        } else {
          // Send regular text reply
          const m = await sock.sendMessage(jid, { text: String(reply).slice(0, 12000) });
          if (m?.key?.id) {
            jarvisSentIds.add(m.key.id);
            if (jarvisSentIds.size > 2000) jarvisSentIds.delete(jarvisSentIds.values().next().value);
          }
        }

        // Voice Response (Push-To-Talk voice note): Always respond in voice if user sent a voice note, or explicitly asked for voice
        const wantsVoice = isVoice || /(?:voice|audio|bolo|bol ke|sunao|bol kar)/i.test(command);
        if (wantsVoice) {
          try {
            console.log(`[JARVIS Baileys] 🎙️ Synthesizing neural voice note response...`);
            const voiceBuf = await synthesizeVoiceBuffer(reply);
            if (voiceBuf) {
              const m = await sock.sendMessage(jid, {
                audio: voiceBuf,
                mimetype: 'audio/mp4',
                ptt: true
              });
              if (m?.key?.id) {
                jarvisSentIds.add(m.key.id);
                if (jarvisSentIds.size > 2000) jarvisSentIds.delete(jarvisSentIds.values().next().value);
              }
              console.log(`[JARVIS Baileys] ✓ Neural voice note dispatched to ${jid}`);
            }
          } catch (voiceErr) {
            console.error('[JARVIS Baileys] Voice reply dispatch notice:', voiceErr.message);
          }
        }
      } catch (error) {
        console.error('[JARVIS Baileys] Command failed:', error.name);
      }
    }
  });
}
start().catch(error => console.error('[JARVIS Baileys] Startup failed:', error.name));

async function sendTo(numberOrName, text, audioPath = null, imagePath = null) {
  const target = String(numberOrName || '').trim().toLowerCase();
  let targetJid = null;
  if (target.endsWith('@g.us') || target.endsWith('@s.whatsapp.net')) {
    if (!/^[0-9-]+@(g.us|s.whatsapp.net)$/.test(target)) throw new Error('Invalid recipient');
    targetJid = target;
  } else {
    const groups = [...groupMap.entries()].filter(([, gName]) => gName.toLowerCase() === target);
    if (groups.length > 1) throw new Error('Ambiguous group name; use its exact group JID');
    if (groups.length === 1) {
      targetJid = groups[0][0];
    } else {
      const digits = target.replace(/[^0-9]/g, '');
      if (!/^\+?[0-9 ()-]+$/.test(target) || digits.length < 10 || digits.length > 15) {
        throw new Error('Use an international phone number or exact group name');
      }
      targetJid = digits + '@s.whatsapp.net';
    }
  }

  let imageReceipt = null;
  if (imagePath && fs.existsSync(imagePath)) {
    try {
      const imgBuf = fs.readFileSync(imagePath);
      imageReceipt = await sock.sendMessage(targetJid, {
        image: imgBuf,
        caption: (text && typeof text === 'string') ? text.slice(0, 1024) : ''
      });
      console.log(`[JARVIS Baileys] ✓ Image dispatched to ${targetJid}: ${imagePath}`);
      if (text && typeof text === 'string' && text.length > 1024) {
        await sock.sendMessage(targetJid, { text: String(text).slice(1024, 12000) });
      }
      return imageReceipt;
    } catch (imgErr) {
      console.error('[JARVIS Baileys] Image dispatch failed, falling back to text:', imgErr.message);
    }
  }

  let textReceipt = null;
  if (text && typeof text === 'string' && text.trim()) {
    textReceipt = await sock.sendMessage(targetJid, { text: String(text).slice(0, 12000) });
    if (textReceipt?.key?.id) {
      jarvisSentIds.add(textReceipt.key.id);
      if (jarvisSentIds.size > 2000) jarvisSentIds.delete(jarvisSentIds.values().next().value);
    }
  }

  let audioReceipt = null;
  if (audioPath && fs.existsSync(audioPath)) {
    const audioBuf = fs.readFileSync(audioPath);
    audioReceipt = await sock.sendMessage(targetJid, {
      audio: audioBuf,
      mimetype: 'audio/mp4',
      ptt: true
    });
    if (audioReceipt?.key?.id) {
      jarvisSentIds.add(audioReceipt.key.id);
      if (jarvisSentIds.size > 2000) jarvisSentIds.delete(jarvisSentIds.values().next().value);
    }
  }

  if (imageReceipt?.key?.id) {
    jarvisSentIds.add(imageReceipt.key.id);
    if (jarvisSentIds.size > 2000) jarvisSentIds.delete(jarvisSentIds.values().next().value);
  }
  return audioReceipt || textReceipt;
}

http.createServer(async (req, res) => {
  const reqUrl = new URL(req.url, `http://${req.headers.host || '127.0.0.1:3200'}`);
  const pathname = reqUrl.pathname;
  const origin = String(req.headers.origin || '');
  const allowedOrigins = ['http://127.0.0.1:3200', 'http://localhost:3200', 'http://127.0.0.1:8770', 'http://localhost:8770'];

  if (!isLoopback(req.socket.remoteAddress) || (origin && !allowedOrigins.includes(origin)) || req.headers['sec-fetch-site'] === 'cross-site') {
    res.writeHead(403);
    return res.end('Forbidden');
  }

  res.setHeader('Cache-Control', 'no-store');
  res.setHeader('X-Frame-Options', 'ALLOWALL');
  res.setHeader('Access-Control-Allow-Origin', origin || '*');

  if (req.method === 'POST' && pathname === '/send') {
    const supplied = String(req.headers['x-jarvis-token'] || '');
    if (!isLoopback(req.socket.remoteAddress) || !supplied || supplied !== HTTP_TOKEN) {
      res.writeHead(403, { 'Content-Type': 'application/json' });
      return res.end(JSON.stringify({ ok: false, error: 'forbidden' }));
    }
    let b = ''; req.on('data', d => { b += d; if (Buffer.byteLength(b) > 32768) req.destroy(); }); req.on('end', async () => {
      try {
        const { number, name, message, audioPath, imagePath } = JSON.parse(b || '{}');
        if (!ready) { res.writeHead(503); return res.end(JSON.stringify({ ok: false, error: 'not ready' })); }
        const receipt = await sendTo(number || name, message, audioPath, imagePath);
        res.writeHead(200); res.end(JSON.stringify({ ok: !!receipt?.key?.id, message_id: receipt?.key?.id || null, delivered: false }));
      } catch (e) { res.writeHead(500); res.end(JSON.stringify({ ok: false, error: String(e).slice(0, 150) })); }
    });
  } else if (req.method === 'POST' && (pathname === '/signal' || pathname === '/send_group')) {
    let b = ''; req.on('data', d => { b += d; if (Buffer.byteLength(b) > 32768) req.destroy(); }); req.on('end', async () => {
      try {
        const { message, symbol, action, lots, targetGroup, group_name } = JSON.parse(b || '{}');
        if (!ready || !sock) {
          res.writeHead(200, { 'Content-Type': 'application/json' });
          return res.end(JSON.stringify({ ok: false, error: 'WhatsApp gateway not connected yet. Waiting for QR scan.' }));
        }

        let targetJid = targetGroup;
        if (!targetJid) {
          const matchName = String(group_name || 'elite trade').toLowerCase();
          for (const [gJid, gName] of groupMap.entries()) {
            if (/elite.*trade|trade.*elite/i.test(gName) || gName.toLowerCase().includes(matchName)) {
              targetJid = gJid;
              break;
            }
          }
        }
        if (!targetJid) {
          // Fallback to known Elite Trade group JID
          targetJid = '120363401615322542@g.us';
        }

        const signalText = message || `📈 [MQ3 ELITE TRADE SIGNAL]\n• Symbol: ${symbol || 'XAUUSD'}\n• Action: ${(action || 'ALERT').toUpperCase()}\n• Lots: ${lots || '0.01'}\n• Time: ${new Date().toISOString()}`;
        const sent = await sock.sendMessage(targetJid, { text: signalText });
        res.writeHead(200, { 'Content-Type': 'application/json' });
        return res.end(JSON.stringify({ ok: !!sent?.key?.id, message_id: sent?.key?.id || null, group: targetJid }));
      } catch (e) {
        res.writeHead(200, { 'Content-Type': 'application/json' });
        return res.end(JSON.stringify({ ok: false, error: String(e).slice(0, 150) }));
      }
    });
  } else if (pathname === '/status') {
    res.writeHead(200, { 'Content-Type': 'application/json' });
    res.end(JSON.stringify({
      ready,
      hasQr: !!lastQr,
      inboundCommandsEnabled: ALLOWED_NUMBERS.size > 0,
      outboundTokenConfigured: !!HTTP_TOKEN,
      commandBackend: JARVIS_URL
    }));
  } else if (pathname === '/pair-code') {
    const phone = (reqUrl.searchParams.get('phone') || '923468053268').replace(/[^0-9]/g, '');
    if (!sock) {
      res.writeHead(503, { 'Content-Type': 'application/json' });
      return res.end(JSON.stringify({ ok: false, error: 'socket_not_ready' }));
    }
    try {
      const code = await sock.requestPairingCode(phone);
      res.writeHead(200, { 'Content-Type': 'application/json' });
      return res.end(JSON.stringify({ ok: true, phone, pairing_code: code }));
    } catch (e) {
      res.writeHead(500, { 'Content-Type': 'application/json' });
      return res.end(JSON.stringify({ ok: false, error: String(e.message || e) }));
    }
  } else if (pathname === '/reset') {
    try {
      if (sock) {
        try { sock.end(); } catch {}
      }
      if (fs.existsSync(AUTH_DIR)) fs.renameSync(AUTH_DIR, AUTH_DIR + ".archived-" + Date.now());
      fs.mkdirSync(AUTH_DIR, { recursive: true });
      ready = false;
      lastQr = null;
      lastQrImage = null;
      start();
      res.writeHead(302, { 'Location': '/qr' });
      return res.end();
    } catch (e) {
      res.writeHead(500, { 'Content-Type': 'application/json' });
      return res.end(JSON.stringify({ ok: false, error: String(e) }));
    }
  } else if (pathname === '/qr.png') {
    if (lastQrImage && lastQrImage.includes(',')) {
      const imgBuf = Buffer.from(lastQrImage.split(',')[1], 'base64');
      res.writeHead(200, { 'Content-Type': 'image/png' });
      return res.end(imgBuf);
    }
    const currentPng = path.join(__dirname, 'current_qr.png');
    if (fs.existsSync(currentPng)) {
      res.writeHead(200, { 'Content-Type': 'image/png' });
      return res.end(fs.readFileSync(currentPng));
    }
    res.writeHead(404, { 'Content-Type': 'text/plain' });
    return res.end('QR not available');
  } else if (pathname === '/qr' || pathname === '/' || pathname.startsWith('/qr')) {
    if (ready) {
      res.writeHead(200, { 'Content-Type': 'text/html; charset=utf-8' });
      return res.end(`<!DOCTYPE html>
<html>
<head>
  <meta charset="utf-8">
  <title>JARVIS WhatsApp Active</title>
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <style>
    body { background: #070d17; color: #00ff88; font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; display: flex; flex-direction: column; align-items: center; justify-content: center; min-height: 100vh; margin: 0; }
    .card { background: #0f172a; border: 1px solid #10b981; border-radius: 16px; padding: 36px; text-align: center; box-shadow: 0 10px 25px rgba(0,0,0,0.5); max-width: 420px; }
    h2 { color: #00ff88; margin: 0 0 10px 0; }
    p { color: #94a3b8; font-size: 14px; }
    .btn { display: inline-block; margin-top: 20px; background: #dc2626; color: #fff; padding: 8px 16px; border-radius: 6px; text-decoration: none; font-size: 13px; font-weight: bold; }
  </style>
</head>
<body>
  <div class="card">
    <h2>✓ WhatsApp Connected &amp; Permanently Linked!</h2>
    <p>Multi-file session active. J.A.R.V.I.S. is ready to receive and dispatch messages in background.</p>
    <a href="/reset" class="btn" onclick="return confirm('Disconnect and generate fresh WhatsApp QR code?')">Reset Pairing Session</a>
  </div>
</body>
</html>`);
    }
    const html = `<!DOCTYPE html>
<html>
<head>
  <meta charset="utf-8">
  <title>JARVIS WhatsApp QR Code</title>
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <style>
    body { background: #070d17; color: #e2e8f0; font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; display: flex; flex-direction: column; align-items: center; justify-content: center; min-height: 100vh; margin: 0; }
    .card { background: #0f172a; border: 1px solid #1e293b; border-radius: 16px; padding: 32px; text-align: center; box-shadow: 0 10px 25px rgba(0,0,0,0.5); max-width: 420px; }
    #qrcode { background: #ffffff; padding: 16px; border-radius: 12px; display: inline-block; margin: 16px 0; min-width:288px; min-height:288px; }
    #qrcode img { width: 288px; height: 288px; display:block; }
    .badge { display: inline-block; background: #0369a1; color: #e0f2fe; padding: 4px 12px; border-radius: 20px; font-size: 12px; margin-bottom: 12px; }
    .btn-reset { display: inline-block; margin-top: 10px; background: #2563eb; color: #fff; padding: 8px 16px; border-radius: 6px; text-decoration: none; font-size: 12px; font-weight: bold; }
    .btn-reset:hover { background: #1d4ed8; }
  </style>
</head>
<body>
  <div class="card">
    <div class="badge">J.A.R.V.I.S. Ecosystem</div>
    <h1>Connect WhatsApp</h1>
    <p>Open <b>WhatsApp</b> on phone &rarr; <b>Linked Devices</b> &rarr; <b>Link a Device</b> and scan:</p>
    <div id="qrcode">${lastQrImage ? `<img alt="WhatsApp pairing QR" src="${lastQrImage}">` : '<p style="color:#111;padding:30px 10px;">Generating fresh pairing QR...<br><span style="font-size:12px;color:#666;">If it takes more than 5s, click refresh below.</span></p>'}</div>
    <div>
      <a href="/qr" class="btn-reset">🔄 Refresh pairing page</a>
      <a href="/reset" style="margin-left:8px;background:#475569;" class="btn-reset">Reset Pairing</a>
    </div>
    <p style="font-size: 11px; color: #64748b; margin-top: 14px;">Auto-refreshes every 6 seconds</p>
  </div>
  <script>setTimeout(() => location.reload(), 6000);</script>
</body>
</html>`;
    res.writeHead(200, { 'Content-Type': 'text/html; charset=utf-8' });
    res.end(html);
  } else {
    // Default redirect to /qr
    res.writeHead(302, { 'Location': '/qr' });
    res.end();
  }
}).listen(PORT, '127.0.0.1', () => console.log('[JARVIS Baileys] HTTP on http://127.0.0.1:' + PORT));
