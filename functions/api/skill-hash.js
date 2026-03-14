// Cloudflare Pages Function - GET /api/skill-hash?slug=xxx
// Returns today's rotating hash URL for a given slug (server-side, algorithm not exposed)
// Secret is server-side only - browser JS never sees the algorithm

const SECRET_SALT = 'ZhaoJiNeng-2026-SkillHub'; // server-side secret

async function slugHashForDate(slug, dateStr) {
  const buf = await crypto.subtle.digest(
    'SHA-256',
    new TextEncoder().encode(SECRET_SALT + '|' + slug + '|' + dateStr)
  );
  return Array.from(new Uint8Array(buf)).map(b => b.toString(16).padStart(2, '0')).join('').slice(0, 24);
}

function utcDate(offsetDays = 0) {
  const d = new Date(Date.now() + offsetDays * 86400000);
  return d.toISOString().slice(0, 10);
}

export async function onRequest(context) {
  const url  = new URL(context.request.url);
  const slug = url.searchParams.get('slug');

  if (!slug) {
    return new Response(JSON.stringify({ error: 'Missing slug' }), {
      status: 400,
      headers: { 'Content-Type': 'application/json', 'Access-Control-Allow-Origin': '*' },
    });
  }

  const date = utcDate(0); // today UTC
  const hash = await slugHashForDate(slug, date);

  return new Response(JSON.stringify({
    slug,
    date,
    hash,
    url: `https://zhaojineng.com/skills/${hash}`,
  }), {
    status: 200,
    headers: {
      'Content-Type': 'application/json',
      'Access-Control-Allow-Origin': '*',
      'Cache-Control': 'no-cache',
    },
  });
}
