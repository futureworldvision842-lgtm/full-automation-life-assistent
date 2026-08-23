const { default: makeWASocket, useMultiFileAuthState, Browsers } = require('@whiskeysockets/baileys');
const pino = require('pino');
const QRCode = require('qrcode');
const fs = require('fs');

const AUTH_DIR = 'E:\\jarvis\\wa\\auth';
const ARTIFACT_QR = 'C:\\Users\\HP\\.gemini\\antigravity\\brain\\d4843218-84b8-421a-ab9e-2517e70e2dd2\\qr.png';

async function main() {
    try {
        if (fs.existsSync(AUTH_DIR)) {
            fs.rmSync(AUTH_DIR, { recursive: true, force: true });
        }
    } catch (e) {
        console.error('Purge error:', e);
    }

    const { state, saveCreds } = await useMultiFileAuthState(AUTH_DIR);
    const sock = makeWASocket({
        auth: state,
        logger: pino({ level: 'silent' }),
        browser: Browsers.ubuntu('Chrome'),
    });

    sock.ev.on('creds.update', saveCreds);
    sock.ev.on('connection.update', async (u) => {
        const { connection, qr } = u;
        if (qr) {
            console.log('[FRESH_QR_TOKEN_RECEIVED]');
            await QRCode.toFile(ARTIFACT_QR, qr, { width: 450, margin: 2 });
            console.log('[QR_IMAGE_SAVED_TO_ARTIFACT]', ARTIFACT_QR);
            process.exit(0);
        }
        if (connection === 'open') {
            console.log('[CONNECTED]');
            process.exit(0);
        }
    });
}

main();
