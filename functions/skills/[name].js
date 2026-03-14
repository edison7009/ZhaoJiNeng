// Cloudflare Pages Function - /skills/:name
// - /skills/xxx.zip  → proxy to Tencent COS (for direct download)
// - /skills/xxx      → resolve available sources, fetch & embed SKILL.md content

const COS_BASE       = 'https://skillhub-1388575217.cos.ap-guangzhou.myqcloud.com/skills';
const CLAWHUB_API    = 'https://wry-manatee-359.convex.site/api/v1/download'; // ClawHub Convex backend
const SKILLS_SH_BASE = 'https://raw.githubusercontent.com/vercel-labs/agent-skills/main/skills';

// HEAD check: 404/410 = truly not found; 405/429/other = exists
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

// Parse ZIP bytes, extract SKILL.md content (handles stored + deflate)
async function extractSkillMdFromZip(zipBytes) {
  const view = new DataView(zipBytes.buffer);
  let offset = 0;

  while (offset < zipBytes.length - 30) {
    const sig = view.getUint32(offset, true);
    if (sig !== 0x04034b50) break; // not a local file header

    const compression   = view.getUint16(offset + 8,  true);
    const compressedSize = view.getUint32(offset + 18, true);
    const filenameLen   = view.getUint16(offset + 26, true);
    const extraLen      = view.getUint16(offset + 28, true);
    const filename      = new TextDecoder().decode(zipBytes.slice(offset + 30, offset + 30 + filenameLen));
    const dataOffset    = offset + 30 + filenameLen + extraLen;

    if (filename === 'SKILL.md' || filename.endsWith('/SKILL.md')) {
      const fileData = zipBytes.slice(dataOffset, dataOffset + compressedSize);
      if (compression === 0) {
        // Stored (no compression)
        return new TextDecoder('utf-8', { fatal: false }).decode(fileData);
      } else if (compression === 8) {
        // Deflate
        const ds     = new DecompressionStream('deflate-raw');
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

    if (compressedSize === 0 && filenameLen === 0) break; // safety
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
  const { params } = context;
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

  const slug        = name;
  const cosZip      = `${COS_BASE}/${slug}.zip`;
  const lightmakeUrl = `https://lightmake.site/api/v1/download?slug=${slug}`;
  const clawhubUrl  = `${CLAWHUB_API}?slug=${slug}`;
  const skillsMdUrl = `${SKILLS_SH_BASE}/${slug}/SKILL.md`;

  // Parallel: check all download sources + fetch SKILL.md text from GitHub if available
  const [cosOk, lightmakeOk, clawhubOk, skillsMdRes] = await Promise.all([
    checkUrl(cosZip),
    checkUrl(lightmakeUrl),
    checkUrl(clawhubUrl),
    fetch(skillsMdUrl, { headers: { 'User-Agent': 'ZhaoJiNeng-Resolver/1.0' }, signal: AbortSignal.timeout(6000) })
      .then(r => r.ok ? r.text() : null).catch(() => null),
  ]);

  let skillMdContent = skillsMdRes || null;

  // If no GitHub SKILL.md, extract from zip (COS preferred, ClawHub fallback)
  if (!skillMdContent && cosOk) {
    skillMdContent = await fetchSkillMdFromZip(cosZip);
  }
  if (!skillMdContent && clawhubOk) {
    skillMdContent = await fetchSkillMdFromZip(clawhubUrl);
  }

  // Build download links (only verified sources)
  const downloadLines = [];
  if (cosOk)        downloadLines.push(`- China Mirror (SkillHub COS): ${cosZip}`);
  if (lightmakeOk)  downloadLines.push(`- lightmake.site: ${lightmakeUrl}`);
  if (clawhubOk)    downloadLines.push(`- ClawHub: ${clawhubUrl}`);

  const skillsMdOk = !!skillsMdRes;
  const mdLines = [];
  if (skillsMdOk) mdLines.push(`- skills.sh / GitHub: ${skillsMdUrl}`);

  const downloadSection = downloadLines.length > 0
    ? downloadLines.join('\n')
    : '- No verified download source found. Please visit https://clawhub.ai or https://zhaojineng.com';

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
