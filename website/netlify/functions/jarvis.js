// Serverless JARVIS brain — keeps the Gemini key SERVER-SIDE (Netlify env var),
// so the public site can talk to JARVIS without ever exposing the key.
exports.handler = async (event) => {
  if (event.httpMethod !== 'POST')
    return { statusCode: 405, body: 'POST only' };
  const KEY = process.env.GEMINI_KEY;
  if (!KEY)
    return { statusCode: 500, body: JSON.stringify({ error: 'server key not set' }) };
  try {
    const b = JSON.parse(event.body || '{}');
    const r = await fetch(
      'https://generativelanguage.googleapis.com/v1beta/models/gemini-flash-latest:generateContent',
      { method: 'POST',
        headers: { 'Content-Type': 'application/json', 'X-goog-api-key': KEY },
        body: JSON.stringify({
          system_instruction: b.system_instruction,
          contents: (b.contents || []).slice(-12),
        }) });
    const j = await r.json();
    return { statusCode: 200, headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(j) };
  } catch (e) {
    return { statusCode: 500, body: JSON.stringify({ error: String(e).slice(0, 120) }) };
  }
};
