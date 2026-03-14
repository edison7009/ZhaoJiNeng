// Cloudflare Pages Function - /skills/:name
// - /skills/xxx.zip       → proxy to Tencent COS (direct download)
// - /skills/{24-hex-hash} → daily-rotating URL, resolves to slug via SHA-256
// - /skills/{slug}        → human-readable (kept for backward compat)

const COS_BASE       = 'https://skillhub-1388575217.cos.ap-guangzhou.myqcloud.com/skills';
const CLAWHUB_API    = 'https://wry-manatee-359.convex.site/api/v1/download';
const SKILLS_SH_BASE = 'https://raw.githubusercontent.com/vercel-labs/agent-skills/main/skills';

// Compute SHA-256(slug + "|" + dateStr), return lower-hex first 24 chars
async function slugHashForDate(slug, dateStr) {
  const buf = await crypto.subtle.digest(
    'SHA-256',
    new TextEncoder().encode(slug + '|' + dateStr)
  );
  return Array.from(new Uint8Array(buf)).map(b => b.toString(16).padStart(2, '0')).join('').slice(0, 24);
}

// UTC date string "YYYY-MM-DD", offsetDays: 0=today, -1=yesterday
function utcDate(offsetDays = 0) {
  const d = new Date(Date.now() + offsetDays * 86400000);
  return d.toISOString().slice(0, 10);
}

// Resolve 24-hex hash → slug by trying today + yesterday against featured slugs
async function resolveHash(hash, origin) {
  try {
    const res = await fetch(`${origin}/public/featured-slugs.json`, { signal: AbortSignal.timeout(5000) });
    if (!res.ok) return null;
    const slugs = await res.json();
    for (const offsetDays of [0, -1]) {
      const date = utcDate(offsetDays);
      for (const slug of slugs) {
        if (await slugHashForDate(slug, date) === hash) return slug;
      }
    }
  } catch {}
  return null;
}

// HEAD check: 404/410 = not found; any other status = exists
async function checkUrl(url) {
  try {
    const res = await fetch(url, {
      method: 'HEAD',
      headers: { 'User-Agent': 'ZhaoJiNeng-Resolver/1.0' },
      signal: AbortSignal.timeout(5000),
    });
    return res.status !== 404 && res.status !== 410;
  } catch {
    return false;
  }
}

// Parse ZIP bytes, extract SKILL.md content (stored + deflate)
async function extractSkillMdFromZip(zipBytes) {
  const view = new DataView(zipBytes.buffer);
  let offset = 0;

  while (offset < zipBytes.length - 30) {
    const sig = view.getUint32(offset, true);
    if (sig !== 0x04034b50) break;

    const compression    = view.getUint16(offset + 8,  true);
    const compressedSize = view.getUint32(offset + 18, true);
    const filenameLen    = view.getUint16(offset + 26, true);
    const extraLen       = view.getUint16(offset + 28, true);
    const filename       = new TextDecoder().decode(zipBytes.slice(offset + 30, offset + 30 + filenameLen));
    const dataOffset     = offset + 30 + filenameLen + extraLen;

    if (filename === 'SKILL.md' || filename.endsWith('/SKILL.md')) {
      const fileData = zipBytes.slice(dataOffset, dataOffset + compressedSize);
      if (compression === 0) {
        return new TextDecoder('utf-8', { fatal: false }).decode(fileData);
      } else if (compression === 8) {
        const ds = new DecompressionStream('deflate-raw');
        const writer = ds.writable.getWriter();
        const reader = ds.readable.getReader();
        writer.write(fileData);
        writer.close();
        const chunks = [];
        while (true) {
          const { done, value } = await reader.read();
          if (done) break;
          chunks.push(value);
        }
        const total = chunks.reduce((a, c) => a + c.length, 0);
        const out   = new Uint8Array(total);
        let pos = 0;
        for (const c of chunks) { out.set(c, pos); pos += c.length; }
        return new TextDecoder('utf-8', { fatal: false }).decode(out);
      }
    }

    if (compressedSize === 0 && filenameLen === 0) break;
    offset = dataOffset + compressedSize;
  }
  return null;
}

// Download zip from a URL and extract SKILL.md
async function fetchSkillMdFromZip(zipUrl) {
  try {
    const res = await fetch(zipUrl, {
      headers: { 'User-Agent': 'ZhaoJiNeng-Resolver/1.0' },
      signal: AbortSignal.timeout(12000),
    });
    if (!res.ok) return null;
    const buf = await res.arrayBuffer();
    return await extractSkillMdFromZip(new Uint8Array(buf));
  } catch {
    return null;
  }
}

export async function onRequest(context) {
  const { params, request } = context;
  const name = params.name;

  // Proxy .zip requests directly to COS
  if (name.endsWith('.zip')) {
    const cosUrl   = `${COS_BASE}/${name}`;
    const response = await fetch(cosUrl, { headers: { 'User-Agent': 'ZhaoJiNeng-Proxy/1.0' } });
    const headers  = new Headers(response.headers);
    headers.set('Access-Control-Allow-Origin', '*');
    headers.set('Cache-Control', 'public, max-age=3600');
    return new Response(response.body, { status: response.status, headers });
  }

  // Resolve 24-char hex hash → slug (daily-rotating URL)
  let slug = name;
  if (/^[0-9a-f]{24}$/.test(name)) {
    const origin   = new URL(request.url).origin;
    const resolved = await resolveHash(name, origin);
    if (!resolved) {
      return new Response(
        'Skill link has expired or is invalid.\nVisit https://zhaojineng.com to get the current link.',
        { status: 404, headers: { 'Content-Type': 'text/plain; charset=utf-8', 'Access-Control-Allow-Origin': '*' } }
      );
    }
    slug = resolved;
  }

  const cosZip       = `${COS_BASE}/${slug}.zip`;
  const lightmakeUrl = `https://lightmake.site/api/v1/download?slug=${slug}`;
  const clawhubUrl   = `${CLAWHUB_API}?slug=${slug}`;
  const skillsMdUrl  = `${SKILLS_SH_BASE}/${slug}/SKILL.md`;

  // Parallel: check all download sources + fetch GitHub SKILL.md text
  const [cosOk, lightmakeOk, clawhubOk, skillsMdRes] = await Promise.all([
    checkUrl(cosZip),
    checkUrl(lightmakeUrl),
    checkUrl(clawhubUrl),
    fetch(skillsMdUrl, { headers: { 'User-Agent': 'ZhaoJiNeng-Resolver/1.0' }, signal: AbortSignal.timeout(6000) })
      .then(r => r.ok ? r.text() : null).catch(() => null),
  ]);

  let skillMdContent = skillsMdRes || null;

  // Extract SKILL.md from zip if not found via GitHub
  if (!skillMdContent && cosOk) {
    skillMdContent = await fetchSkillMdFromZip(cosZip);
  }
  if (!skillMdContent && clawhubOk) {
    skillMdContent = await fetchSkillMdFromZip(clawhubUrl);
  }

  const downloadLines = [];
  if (cosOk)       downloadLines.push(`- China Mirror (SkillHub COS): ${cosZip}`);
  if (lightmakeOk) downloadLines.push(`- lightmake.site: ${lightmakeUrl}`);
  if (clawhubOk)   downloadLines.push(`- ClawHub: ${clawhubUrl}`);

  const skillsMdOk = !!skillsMdRes;
  const mdLines = [];
  if (skillsMdOk) mdLines.push(`- skills.sh / GitHub: ${skillsMdUrl}`);

  const downloadSection = downloadLines.length > 0
    ? downloadLines.join('\n')
    : '- No verified download source found. Visit https://clawhub.ai or https://zhaojineng.com';

  const skillMdSection = skillMdContent
    ? `\n## SKILL.md Content\n\nThis is the full content of the skill. Read it to understand what this skill does.\n\n${skillMdContent}\n`
    : '';

  const content = `# Skill: ${slug}

This is a machine-readable skill descriptor for AI agents.
Human users: visit https://zhaojineng.com to browse and download skills.
${skillMdSection}
## Download Links (zip)

${downloadSection}
${mdLines.length > 0 ? '\n## SKILL.md Sources (markdown format)\n\n' + mdLines.join('\n') : ''}

## Official Pages

- ClawHub: https://clawhub.ai/skills/${slug}
- ZhaoJiNeng: https://zhaojineng.com/skills/${slug}

## Skill Info

- Slug: ${slug}
- Registry: https://zhaojineng.com
- Source: ClawHub / SkillHub / skills.sh

## Agent Instructions

If you are an AI agent reading this file, please:
1. Read the "SKILL.md Content" section above — it contains the full skill instructions
2. Download the zip from "Download Links" if you need additional script files
3. Extract the zip to the appropriate skills directory
4. Confirm installation to the user
`;

  return new Response(content, {
    status: 200,
    headers: {
      'Content-Type': 'text/plain; charset=utf-8',
      'Access-Control-Allow-Origin': '*',
      'Cache-Control': 'no-cache',
    },
  });
}
