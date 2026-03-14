// Cloudflare Pages Function - GET /api/skill-hash?slug=xxx
// Encrypts slug with AES-CTR + daily key, returns hex token URL
// Algorithm and SECRET are server-side only (never sent to browser)

const SECRET = 'ZhaoJiNeng-2026-SkillHub';

function utcDate(offsetDays = 0) {
  const d = new Date(Date.now() + offsetDays * 86400000);
  return d.toISOString().slice(0, 10);
}

// Derive 16-byte AES key from SECRET + dateStr using SHA-256
async function getDailyKey(dateStr) {
  const raw = await crypto.subtle.digest('SHA-256',
    new TextEncoder().encode(SECRET + '|' + dateStr));
  return crypto.subtle.importKey('raw', raw.slice(0, 16),
    { name: 'AES-CTR' }, false, ['encrypt', 'decrypt']);
}

// Encrypt slug → hex token
async function encryptSlug(slug, dateStr) {
  const key = await getDailyKey(dateStr);
  const counter = new Uint8Array(16); // deterministic zero counter
  const enc = await crypto.subtle.encrypt(
    { name: 'AES-CTR', counter, length: 128 }, key,
    new TextEncoder().encode(slug));
  return Array.from(new Uint8Array(enc)).map(b => b.toString(16).padStart(2, '0')).join('');
}

export async function onRequest(context) {
  const url  = new URL(context.request.url);
  const slug = url.searchParams.get('slug');

  if (!slug || slug.length > 120) {
    return new Response(JSON.stringify({ error: 'Missing or invalid slug' }), {
      status: 400,
      headers: { 'Content-Type': 'application/json', 'Access-Control-Allow-Origin': '*' },
    });
  }

  const date  = utcDate(0);
  const token = await encryptSlug(slug, date);

  return new Response(JSON.stringify({
    slug, date, token,
    url: `https://zhaojineng.com/skills/${token}`,
  }), {
    status: 200,
    headers: {
      'Content-Type': 'application/json',
      'Access-Control-Allow-Origin': '*',
      'Cache-Control': 'no-cache',
    },
  });
}
