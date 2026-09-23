// Keep this invocation and its npm children on the explicitly selected Node runtime.
// This does not alter the user's global Node installation or system environment.
import { dirname, delimiter } from 'node:path';
process.env.PATH = dirname(process.execPath) + delimiter + (process.env.PATH || '');
// Browser QA is opt-in; dependency installation does not need another browser.
if (process.argv.some(arg => arg.endsWith('install-dependencies.mjs'))) {
  process.env.PUPPETEER_SKIP_DOWNLOAD = 'true';
}
