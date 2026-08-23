const { default: makeWASocket, useMultiFileAuthState } = require('@whiskeysockets/baileys');
const pino = require('pino');
const QRCode = require('qrcode');
const fs = require('fs');

const AUTH_DIR = 'E:\\jarvis\\wa\\auth';
const ARTIFACT_QR = 'C:\\Users\\HP\\.gemini\\antigravity\\brain\\d4843218-84b8-421a-ab9e-2517e70e2dd2\\qr.png';

async function generate() {
    // Clear stale auth files if not yet connected
    try {
        if (fs.existsSync(AUTH_DIR)) {
            const files = fs.readdirSync(AUTH_DIR);
            for (const f of files) {
                if (f.startsWith('app-state-') || f.startsWith('pre-key-') || f === 'creds.json') {
                    fs.unlinkSync(`${AUTH_DIR}/${f}`);
                }
            }
        }
    } catch (e) {
        console.error('Clean error:', e);
    }

    const { state, saveCreds } = await useMultiFileAuthState(AUTH_DIR);
    const sock = makeWASocket({
        auth: state,
        logger: pino({ level: 'silent' }),
        browser: ['JARVIS', 'Chrome', '1.0']
    });

    sock.ev.on('creds.update', saveCreds);
    sock.ev.on('connection.update', async (u) => {
        const { connection, qr } = u;
        if (qr) {
            console.log('[QR Received] Generating image...');
            await QRCode.toFile(ARTIFACT_QR, qr, { width: 450, margin: 2 });
            console.log('[QR Image Saved]', ARTIFACT_QR);
            process.exit(0);
        }
        if (connection === 'open') {
            console.log('[Already Connected]');
            process.exit(0);
        }
    });
}

generate();
