const { default: makeWASocket, useMultiFileAuthState, Browsers } = require('@whiskeysockets/baileys');
const pino = require('pino');
const qrcode = require('qrcode-terminal');
const fs = require('fs');

const AUTH_DIR = 'E:\\jarvis\\wa\\auth';

async function test() {
  try {
    if (fs.existsSync(AUTH_DIR)) {
      fs.rmSync(AUTH_DIR, { recursive: true, force: true });
    }
  } catch (e) {}

  const { fetchLatestBaileysVersion } = require('@whiskeysockets/baileys');
  const { version } = await fetchLatestBaileysVersion();
  console.log('Fetched WA Version:', version.join('.'));

  const { state, saveCreds } = await useMultiFileAuthState(AUTH_DIR);
  
  const sock = makeWASocket({
    version,
    auth: state,
    logger: pino({ level: 'silent' }),
    browser: ['Mac OS', 'Chrome', '120.0.0.0'],
    syncFullHistory: false
  });

  sock.ev.on('creds.update', saveCreds);
  sock.ev.on('connection.update', (u) => {
    const { connection, lastDisconnect, qr } = u;
    if (qr) {
      console.log('SUCCESS_QR_GENERATED');
      qrcode.generate(qr, { small: true });
    }
    if (connection === 'close') {
      const code = lastDisconnect && lastDisconnect.error && lastDisconnect.error.output && lastDisconnect.error.output.statusCode;
      console.log('CLOSED_WITH_CODE:', code);
    }
    if (connection === 'open') {
      console.log('CONNECTED_OPEN');
    }
  });
}

test();
