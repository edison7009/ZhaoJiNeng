// Cloudflare Pages Function - /skills/:name
// - /skills/xxx.zip  → proxy to Tencent COS (for direct download)
// - /skills/xxx      → resolve available download sources, return AI-readable metadata

const COS_BASE = 'https://skillhub-1388575217.cos.ap-guangzhou.myqcloud.com/skills';
const CLAWHUB_API = 'https://wry-manatee-359.convex.site/api/v1/download';

// Check if a URL is accessible (HEAD request, fast)
async function checkUrl(url) {
  try {
    const res = await fetch(url, {
      method: 'HEAD',
      headers: { 'User-Agent': 'ZhaoJiNeng-Resolver/1.0' },
      signal: AbortSignal.timeout(5000),
    });
    return res.ok;
  } catch {
    return false;
  }
}

export async function onRequest(context) {
  const { params } = context;
  const name = params.name;

  // If requesting a .zip file, proxy directly to COS
  if (name.endsWith('.zip')) {
    const cosUrl = `${COS_BASE}/${name}`;
    const response = await fetch(cosUrl, {
      headers: { 'User-Agent': 'ZhaoJiNeng-Proxy/1.0' },
    });
    const headers = new Headers(response.headers);
    headers.set('Access-Control-Allow-Origin', '*');
    headers.set('Cache-Control', 'public, max-age=3600');
    return new Response(response.body, { status: response.status, headers });
  }

  // Resolve available download sources in parallel
  const slug = name;
  const cosZip = `${COS_BASE}/${slug}.zip`;
  const clawhubUrl = `${CLAWHUB_API}?slug=${slug}`;
  const lightmakeUrl = `https://lightmake.site/api/v1/download?slug=${slug}`;

  const [cosOk, clawhubOk, lightmakeOk] = await Promise.all([
    checkUrl(cosZip),
    checkUrl(clawhubUrl),
    checkUrl(lightmakeUrl),
  ]);

  // Build download links list (only include verified sources)
  const downloadLines = [];
  if (cosOk)       downloadLines.push(`- China Mirror (SkillHub COS): ${cosZip}`);
  if (lightmakeOk) downloadLines.push(`- lightmake.site: ${lightmakeUrl}`);
  if (clawhubOk)   downloadLines.push(`- ClawHub: ${clawhubUrl}`);

  const downloadSection = downloadLines.length > 0
    ? downloadLines.join('\n')
    : '- No verified download source found. Please visit https://clawhub.ai or https://zhaojineng.com';

  const content = `# Skill: ${slug}

This is a machine-readable skill descriptor for AI agents.
Human users: visit https://zhaojineng.com to browse and download skills.

## Install Instructions

To install this skill, download the zip file and extract it to your agent's skills directory.

## Download Links

${downloadSection}

## Official Pages

- ClawHub: https://clawhub.ai/skills/${slug}
- ZhaoJiNeng: https://zhaojineng.com/skills/${slug}

## Skill Info

- Slug: ${slug}
- Registry: https://zhaojineng.com
- Source: ClawHub / SkillHub

## Agent Instructions

If you are an AI agent reading this file, please:
1. Download the zip from the first available link above
2. Extract the contents to the appropriate skills directory
3. Confirm installation to the user
`;

  return new Response(content, {
    status: 200,
    headers: {
      'Content-Type': 'text/plain; charset=utf-8',
      'Access-Control-Allow-Origin': '*',
      'Cache-Control': 'no-cache', // Dynamic content - do not cache
    },
  });
}
