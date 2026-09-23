import makeWASocket, {
  DisconnectReason,
  useMultiFileAuthState,
  fetchLatestBaileysVersion,
  downloadMediaMessage
} from '@whiskeysockets/baileys';
import pino from 'pino';
import qrcodeTerminal from 'qrcode-terminal';
import QRCode from 'qrcode';
import express from 'express';
import http from 'http';
import fs from 'fs';
import path from 'path';
import crypto from 'crypto';
import { fileURLToPath } from 'url';

const app = express();
app.use(express.json({ limit: '50mb' }));

const PORT = 3001;
const BRIDGE_DIR = path.dirname(fileURLToPath(import.meta.url));
const AUTH_DIR = path.join(BRIDGE_DIR, 'whatsapp_auth');
const TOKEN_FILE = path.join(BRIDGE_DIR, '..', 'runtime', 'bridge_token.txt');
function getBridgeToken() {
  if (process.env.MQ3_BRIDGE_TOKEN) return process.env.MQ3_BRIDGE_TOKEN.trim();
  if (fs.existsSync(TOKEN_FILE)) {
    try {
      return fs.readFileSync(TOKEN_FILE, 'utf-8').replace(/^\uFEFF/, '').trim();
    } catch (e) {}
  }
  return '';
}
const DASHBOARD_BASE_URL = (process.env.MQ3_DASHBOARD_BASE_URL || 'http://127.0.0.1:5050').replace(/\/$/, '');

function requireBridgeToken(req, res, next) {
  const token = getBridgeToken();
  if (!token) {
    return res.status(503).json({ error: 'Bridge mutation token is not configured' });
  }
  const supplied = String(req.get('X-MQ3-Bridge-Token') || '').trim();
  const expectedBuffer = Buffer.from(token);
  const suppliedBuffer = Buffer.from(supplied);
  if (
    suppliedBuffer.length !== expectedBuffer.length ||
    !crypto.timingSafeEqual(suppliedBuffer, expectedBuffer)
  ) {
    return res.status(401).json({ error: 'Unauthorized bridge mutation request' });
  }
  return next();
}

let sock = null;
let currentQR = null;
let currentQRImage = null;
let isConnected = false;
let connectedUser = null;
let connectedUserLid = null;
let reconnectAttempts = 0;
let lastConnectedAt = null;
let lastDisconnectedAt = null;
let lastDisconnectCode = null;
const MAX_BACKOFF_MS = 30000;

// ── AUTHORIZED CONTACTS WHITELIST ──────────────────────────────────────────
const ALLOWED_NUMBERS = new Set([
  '923468053268' // Master Owner (Connected)
]);
const ALLOWED_LIDS = new Set();
const ELITE_TRADE_GROUP_ID = '120363401615322542@g.us';

export function isAuthorizedContact(jid, msg, ownerLid = null) {
  if (msg && msg.key && msg.key.fromMe) return true;
  if (!jid || typeof jid !== 'string') return false;
  const cleanJid = jid.trim();

  // Block null-bytes and control character injection attempts
  if (/[\x00-\x1f\x7f]/.test(cleanJid)) return false;

  // Allow Elite Trade Group
  if (cleanJid === ELITE_TRADE_GROUP_ID || cleanJid.startsWith('120363401615322542@g.us')) return true;

  // Drop broadcasts
  if (cleanJid === 'status@broadcast' || cleanJid.includes('broadcast')) return false;

  // Reject unapproved groups
  if (cleanJid.endsWith('@g.us') || cleanJid.includes('@g.us')) return false;

  // Strict LID (Linked Identity Device) verification — eliminate wildcard vulnerability
  if (cleanJid.endsWith('@lid') || cleanJid.includes('@lid')) {
    const rawLid = cleanJid.split('@')[0].split(':')[0].trim();
    const activeOwnerLid = ownerLid || connectedUserLid;
    if (activeOwnerLid) {
      const activeRaw = activeOwnerLid.split('@')[0].split(':')[0].trim();
      if (rawLid === activeRaw || cleanJid.startsWith(activeRaw)) {
        return true;
      }
    }
    return ALLOWED_LIDS.has(rawLid) || ALLOWED_LIDS.has(cleanJid);
  }

  // Standard Phone JID verification
  let rawPhone = cleanJid;
  if (cleanJid.includes('@')) {
    const parts = cleanJid.split('@');
    if (parts.length !== 2) return false;
    rawPhone = parts[0].trim();
    const domain = parts[1].trim();
    if (domain !== 's.whatsapp.net') return false;
  }
  if (rawPhone.includes(':')) {
    const subparts = rawPhone.split(':');
    if (subparts.length !== 2 || !/^\d+$/.test(subparts[1])) return false;
    rawPhone = subparts[0].trim();
  }

  if (!/^\+?[0-9\s\-]+$/.test(rawPhone)) {
    return false;
  }

  let clean = rawPhone.replace(/[^0-9]/g, '');
  if (clean.startsWith('0092') && clean.length === 14) {
    clean = clean.slice(2);
  } else if (clean.startsWith('0') && clean.length === 11) {
    clean = '92' + clean.slice(1);
  }
  return ALLOWED_NUMBERS.has(clean);
}

const botSentMessageIds = new Set();

async function initWhatsApp() {
  if (!fs.existsSync(AUTH_DIR)) {
    fs.mkdirSync(AUTH_DIR, { recursive: true });
  }

  // Clean up any existing socket instance
  if (sock) {
    try {
      sock.ev.removeAllListeners();
      sock.end(undefined);
    } catch (e) {
      // ignore
    }
    sock = null;
  }

  const { state, saveCreds } = await useMultiFileAuthState(AUTH_DIR);
  const { version } = await fetchLatestBaileysVersion();

  console.log('\n================================================================');
  console.log('       TRADING BOT — WHATSAPP MULTI-DEVICE QR BRIDGE            ');
  console.log('   [STRICT WHITELIST SECURITY ACTIVE: SINGLE OWNER & ELITE TRADE GROUP ONLY] ');
  console.log('================================================================\n');

  sock = makeWASocket({
    version,
    logger: pino({ level: 'silent' }),
    printQRInTerminal: false,
    auth: state,
    browser: ['Trading Bot AI', 'Chrome', '1.0.0']
  });

  sock.ev.on('creds.update', saveCreds);

  sock.ev.on('connection.update', async (update) => {
    const { connection, lastDisconnect, qr } = update;

    if (qr) {
      currentQR = qr;
      try {
        currentQRImage = await QRCode.toDataURL(qr);
      } catch (err) {
        console.error('QR generation error:', err);
      }

      console.log('\n📱 SCAN THIS QR CODE WITH WHATSAPP (Linked Devices -> Link a Device):');
      qrcodeTerminal.generate(qr, { small: true });
      console.log(`Or scan via Dashboard: ${DASHBOARD_BASE_URL}/whatsapp\n`);
    }

    if (connection === 'close') {
      isConnected = false;
      connectedUser = null;
      connectedUserLid = null;
      currentQR = null;
      currentQRImage = null;

      const statusCode = (lastDisconnect?.error)?.output?.statusCode;
      lastDisconnectedAt = new Date().toISOString();
      lastDisconnectCode = statusCode ?? null;
      console.log(`[WhatsApp Bridge] Connection closed with status code: ${statusCode}`);

      if (statusCode === DisconnectReason.loggedOut) {
        console.log('[WhatsApp Bridge] Session logged out (401). Resetting auth directory for new pairing...');
        try {
          fs.rmSync(AUTH_DIR, { recursive: true, force: true });
        } catch (e) {}
        reconnectAttempts = 0;
        setTimeout(initWhatsApp, 1000);
        return;
      }

      if (statusCode === DisconnectReason.restartRequired || statusCode === 515) {
        console.log('[WhatsApp Bridge] Server requested restart (515). Reconnecting immediately...');
        setTimeout(initWhatsApp, 500);
        return;
      }

      // Exponential backoff for transient disconnects (408, 500, 503, connectionClosed)
      reconnectAttempts++;
      const delay = Math.min(2000 * Math.pow(1.5, reconnectAttempts - 1), MAX_BACKOFF_MS);
      console.log(`[WhatsApp Bridge] Reconnecting in ${Math.round(delay)}ms (attempt ${reconnectAttempts})...`);
      setTimeout(initWhatsApp, delay);

    } else if (connection === 'open') {
      isConnected = true;
      reconnectAttempts = 0;
      currentQR = null;
      currentQRImage = null;
      connectedUser = sock.user?.id || 'Connected';
      connectedUserLid = sock.user?.lid || null;
      lastConnectedAt = new Date().toISOString();
      lastDisconnectCode = null;

      if (connectedUserLid) {
        ALLOWED_LIDS.add(connectedUserLid.split('@')[0].split(':')[0].trim());
        ALLOWED_LIDS.add(connectedUserLid);
      }
      if (sock.user?.id) {
        const rawId = sock.user.id.split('@')[0].split(':')[0].trim();
        ALLOWED_NUMBERS.add(rawId);
      }

      console.log('\n================================================================');
      console.log(`✅ WHATSAPP CONNECTED SUCCESSFULLY as ${connectedUser}!`);
      if (connectedUserLid) {
        console.log(`🔒 Verified Connected Owner LID: ${connectedUserLid}`);
      }
      console.log('================================================================\n');
    }
  });

  // Handle Incoming WhatsApp Messages & Commands
  sock.ev.on('messages.upsert', async ({ messages, type }) => {
    if (type !== 'notify' && type !== 'append') return;
    for (const msg of messages) {
      if (!msg.message) continue;

      const msgId = msg.key?.id;
      if (msgId && botSentMessageIds.has(msgId)) {
        continue;
      }

      const from = msg.key.remoteJid;
      if (!from || from === 'status@broadcast' || from.includes('broadcast')) continue;

      const isGroup = from.endsWith('@g.us');
      const participant = msg.key?.participant || (isGroup ? '' : from);

      // 🔒 STRICT WHITELIST GATE: Drop unapproved groups or senders immediately & silently
      if (isGroup) {
        if (!from.startsWith('120363401615322542')) {
          continue; // Silent drop
        }
      } else {
        if (!isAuthorizedContact(from, msg, connectedUserLid)) {
          continue; // Silent drop
        }
      }
      const BRIDGE_TOKEN = getBridgeToken();

      // Handle Voice Notes (PTT audio / audioMessage)
      if (msg.message.audioMessage) {
        try {
          // 1. Immediate visual tactile feedback reaction (<100ms)
          try {
            await sock.sendMessage(from, { react: { text: "🎙️", key: msg.key } });
          } catch (e) {}

          // 2. Download and decrypt audio buffer
          const buffer = await downloadMediaMessage(
            msg,
            'buffer',
            {},
            { logger: pino({ level: 'silent' }), reuploadRequest: sock.updateMediaMessage }
          );

          if (buffer && buffer.length > 0) {
            // 3. Dispatch to Python Audio Processing Webhook
            const audioPayload = {
              sender: from,
              participant: participant || from,
              isGroup,
              // Set only after the strict owner/LID gate above. Python accepts
              // this proof only on the token-authenticated local webhook.
              bridge_verified_owner: !isGroup,
              messageType: 'audio',
              audio_base64: buffer.toString('base64'),
              mimetype: msg.message.audioMessage.mimetype || 'audio/ogg; codecs=opus',
              is_ptt: !!msg.message.audioMessage.ptt,
              duration: msg.message.audioMessage.seconds || 0,
              msg_id: msgId
            };

            const response = await fetch(`${DASHBOARD_BASE_URL}/api/whatsapp_audio`, {
              method: 'POST',
              headers: {
                'Content-Type': 'application/json',
                'X-MQ3-Bridge-Token': BRIDGE_TOKEN
              },
              body: JSON.stringify(audioPayload)
            });

            if (response.ok) {
              const data = await response.json();
              const replyText = data.reply || data.response;
              if (replyText) {
                const sent = await sock.sendMessage(from, { text: replyText });
                if (sent?.key?.id) botSentMessageIds.add(sent.key.id);
                const reactionEmoji = data.action_executed ? "⚡" : "✅";
                try {
                  await sock.sendMessage(from, { react: { text: reactionEmoji, key: msg.key } });
                } catch (e) {}
              }
            } else {
              try {
                await sock.sendMessage(from, { react: { text: "⚠️", key: msg.key } });
              } catch (e) {}
            }
          }
        } catch (err) {
          try {
            await sock.sendMessage(from, { react: { text: "⚠️", key: msg.key } });
          } catch (e) {}
        }
        continue;
      }

      // Handle Text Messages
      const text = msg.message.conversation ||
                   msg.message.extendedTextMessage?.text ||
                   msg.message.imageMessage?.caption ||
                   msg.message.videoMessage?.caption ||
                   '';

      if (!text || !text.trim()) {
        continue;
      }

      const trimmedText = text.trim();
      console.log(`[WhatsApp Bridge] 📨 Received message from ${from}: "${trimmedText}"`);
      // Forward to the configured local Python Bot API.
      try {
        const response = await fetch(`${DASHBOARD_BASE_URL}/api/whatsapp_command`, {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            'X-MQ3-Bridge-Token': BRIDGE_TOKEN
          },
          body: JSON.stringify({
            sender: from,
            participant: participant || from,
            isGroup,
            bridge_verified_owner: !isGroup,
            message: trimmedText,
            command: trimmedText
          })
        });

        if (response.ok) {
          const data = await response.json();
          const replyText = data.reply || data.response;
          if (replyText) {
            console.log(`[WhatsApp Bridge] 📤 Replying to ${from}...`);
            const sent = await sock.sendMessage(from, { text: replyText });
            if (sent?.key?.id) {
              botSentMessageIds.add(sent.key.id);
            }
          }
        } else {
          console.error(`[WhatsApp Bridge] ❌ Dashboard responded with status ${response.status}:`, await response.text());
        }
      } catch (err) {
        console.error(`[WhatsApp Bridge] ❌ Forwarding error:`, err.message);
      }
    }
  });
}

// REST API Endpoints for Python Bot
app.get('/status', (req, res) => {
  res.json({
    connected: isConnected,
    user: connectedUser,
    user_lid: connectedUserLid,
    has_qr: !!currentQR,
    qr_data: currentQR,
    qr_image: currentQRImage,
    allowed_contacts_count: ALLOWED_NUMBERS.size,
    session_persistence: fs.existsSync(path.join(AUTH_DIR, 'creds.json')) ? 'SAVED_MULTI_FILE_AUTH' : 'AWAITING_PAIRING',
    saved_session_present: fs.existsSync(path.join(AUTH_DIR, 'creds.json')),
    reconnect_attempts: reconnectAttempts,
    last_connected_at: lastConnectedAt,
    last_disconnected_at: lastDisconnectedAt,
    last_disconnect_code: lastDisconnectCode
  });
});

app.post('/reset_pairing', requireBridgeToken, async (req, res) => {
  console.log('[WhatsApp Bridge] Resetting pairing session and generating fresh QR code...');
  try {
    if (sock) {
      sock.ev.removeAllListeners();
      sock.end(undefined);
      sock = null;
    }
    fs.rmSync(AUTH_DIR, { recursive: true, force: true });
  } catch (e) {}
  isConnected = false;
  connectedUser = null;
  currentQR = null;
  currentQRImage = null;
  setTimeout(initWhatsApp, 500);
  res.json({ success: true, message: 'Pairing reset initiated. Fresh QR generating...' });
});

app.get('/qr', (req, res) => {
  if (isConnected) {
    return res.send(`<html><body style="background:#111;color:#0f0;font-family:sans-serif;text-align:center;padding:50px;">
      <h2>✅ WhatsApp Connected</h2><p>Linked as: ${connectedUser}</p>
    </body></html>`);
  }
  if (currentQRImage) {
    return res.send(`<html><body style="background:#111;color:#fff;font-family:sans-serif;text-align:center;padding:50px;">
      <h2>📱 Scan with WhatsApp (Linked Devices)</h2>
      <img src="${currentQRImage}" style="border:10px solid #fff;border-radius:8px;margin:20px auto;" />
      <p>Scan using your phone's WhatsApp</p>
      <script>setTimeout(() => location.reload(), 5000);</script>
    </body></html>`);
  }
  res.send('<html><body style="background:#111;color:#aaa;font-family:sans-serif;text-align:center;padding:50px;"><h2>Generating QR Code...</h2><script>setTimeout(() => location.reload(), 2000);</script></body></html>');
});

app.get('/groups', async (req, res) => {
  if (!sock || !isConnected) {
    return res.status(503).json({ error: 'WhatsApp not connected' });
  }
  try {
    const groups = await sock.groupFetchAllParticipating();
    const list = Object.values(groups).map(g => ({ id: g.id, subject: g.subject }));
    res.json({ groups: list });
  } catch (err) {
    res.status(500).json({ error: err.message });
  }
});

app.post('/send_group', requireBridgeToken, async (req, res) => {
  const { group_name, message } = req.body;
  if (!sock || !isConnected) {
    return res.status(503).json({ error: 'WhatsApp not connected' });
  }

  try {
    const groups = await sock.groupFetchAllParticipating();
    let targetGroup = Object.values(groups).find(g =>
      g.subject.toLowerCase().includes((group_name || 'elite trade').toLowerCase())
    );

    if (!targetGroup) {
      if (group_name && group_name.includes('@g.us')) {
        targetGroup = { id: group_name, subject: 'Direct Group JID' };
      } else {
        return res.status(404).json({ error: `Group '${group_name}' not found on linked WhatsApp account.` });
      }
    }

    await sock.sendMessage(targetGroup.id, { text: message });
    res.json({ success: true, group_id: targetGroup.id, group_name: targetGroup.subject });
  } catch (err) {
    res.status(500).json({ error: err.message });
  }
});

app.post('/send', requireBridgeToken, async (req, res) => {
  const { to, message } = req.body;
  if (!sock || !isConnected) {
    return res.status(503).json({ error: 'WhatsApp not connected' });
  }

  try {
    let target = ELITE_TRADE_GROUP_ID;
    if (to) {
      if (isAuthorizedContact(to, null, connectedUserLid)) {
        target = to.includes('@') ? to : `${to.replace(/[^0-9]/g, '')}@s.whatsapp.net`;
      } else if (to === ELITE_TRADE_GROUP_ID || to.startsWith('120363401615322542')) {
        target = to;
      }
    }
    await sock.sendMessage(target, { text: message });
    return res.json({ success: true, recipient: target, requested_to: to });
  } catch (err) {
    res.status(500).json({ error: err.message });
  }
});

// Process-level uncaught exceptions handler
process.on('uncaughtException', (err) => {
  console.error('[WhatsApp Bridge UncaughtException]:', err.message);
});
process.on('unhandledRejection', (reason) => {
  console.error('[WhatsApp Bridge UnhandledRejection]:', reason);
});

app.listen(PORT, '127.0.0.1', () => {
  console.log(`WhatsApp Bridge HTTP API listening on http://127.0.0.1:${PORT}`);
  initWhatsApp();
});
