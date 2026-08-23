const { default: makeWASocket, useMultiFileAuthState, Browsers, fetchLatestBaileysVersion } = require('@whiskeysockets/baileys');
const pino = require('pino');
const fs = require('fs');

const AUTH_DIR = 'E:\\jarvis\\wa\\auth';
const phoneNum = '923468053268'; // Boss phone number

async function testPairing() {
  try {
    if (fs.existsSync(AUTH_DIR)) {
      fs.rmSync(AUTH_DIR, { recursive: true, force: true });
    }
  } catch (e) {}

  const { version } = await fetchLatestBaileysVersion();
  const { state, saveCreds } = await useMultiFileAuthState(AUTH_DIR);
  
  const sock = makeWASocket({
    version,
    auth: state,
    logger: pino({ level: 'silent' }),
    browser: Browsers.ubuntu('Chrome'),
    syncFullHistory: false
  });

  sock.ev.on('creds.update', saveCreds);
  sock.ev.on('connection.update', (u) => {
    const { connection, lastDisconnect } = u;
    if (connection === 'open') {
      console.log('PAIRING_CODE_CONNECTED_SUCCESS!');
      process.exit(0);
    }
    if (connection === 'close') {
      console.log('CLOSED:', lastDisconnect && lastDisconnect.error);
    }
  });

  setTimeout(async () => {
    try {
      const code = await sock.requestPairingCode(phoneNum);
      console.log('\n========================================');
      console.log(`[JARVIS PAIRING CODE]: ${code}`);
      console.log('========================================\n');
    } catch (err) {
      console.error('Pairing Code Error:', err);
    }
  }, 3000);
}

testPairing();
