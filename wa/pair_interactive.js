const { default: makeWASocket, useMultiFileAuthState, Browsers, fetchLatestBaileysVersion, DisconnectReason } = require('@whiskeysockets/baileys');
const pino = require('pino');
const fs = require('fs');
const path = require('path');

const AUTH_DIR = path.join(__dirname, 'wa_auth');
const targetPhone = process.argv[2] || '923468053268';

async function pairDevice() {
  console.log(`\n[JARVIS Pair Tool] Resetting auth directory for phone: ${targetPhone}...`);
  fs.rmSync(AUTH_DIR, { recursive: true, force: true });

  const { version } = await fetchLatestBaileysVersion();
  const { state, saveCreds } = await useMultiFileAuthState(AUTH_DIR);

  const sock = makeWASocket({
    version,
    auth: state,
    logger: pino({ level: 'silent' }),
    browser: ['Ubuntu', 'Chrome', '20.0.04'],
    syncFullHistory: false
  });

  sock.ev.on('creds.update', saveCreds);

  sock.ev.on('connection.update', (u) => {
    const { connection, lastDisconnect } = u;
    if (connection === 'open') {
      console.log('\n==================================================');
      console.log('🎉 [JARVIS] SUCCESS! WhatsApp linked & authenticated permanently!');
      console.log('==================================================\n');
      process.exit(0);
    }
    if (connection === 'close') {
      const code = lastDisconnect?.error?.output?.statusCode;
      console.log(`[JARVIS Pair Tool] Disconnected with code: ${code}`);
      if (code === DisconnectReason.loggedOut) {
        console.log('[JARVIS Pair Tool] Session logged out. Try running again.');
        process.exit(1);
      }
    }
  });

  setTimeout(async () => {
    try {
      const cleanNumber = targetPhone.replace(/[^0-9]/g, '');
      const code = await sock.requestPairingCode(cleanNumber);
      console.log('\n==================================================');
      console.log(`📱 [PHONE NUMBER]: +${cleanNumber}`);
      console.log(`🔑 [PAIRING CODE]: ${code}`);
      console.log('==================================================');
      console.log('Open WhatsApp > Linked Devices > Link with phone number instead and enter the code above.\n');
    } catch (err) {
      console.error('[JARVIS Pair Tool] Error requesting pairing code:', err);
    }
  }, 2500);
}

pairDevice();
