// Cloudflare Pages Function - /skills/:name
// - /skills/xxx.zip  → proxy to Tencent COS (for direct download)
// - /skills/xxx      → resolve available download sources, return AI-readable metadata

const COS_BASE    = 'https://skillhub-1388575217.cos.ap-guangzhou.myqcloud.com/skills';
const CLAWHUB_API = 'https://clawhub.ai/api/v1/download';  // DEFAULT_REGISTRY from clawhub CLI
const SKILLS_SH_BASE = 'https://raw.githubusercontent.com/vercel-labs/agent-skills/main/skills';

// Check if a URL is accessible (HEAD request, fast)
// 404 = not found (skip); 405 = HEAD not allowed but URL exists (ok); 429 = rate limited but URL exists (ok)
async function checkUrl(url) {
  try {
    const res = await fetch(url, {
      method: 'HEAD',
      headers: { 'User-Agent': 'ZhaoJiNeng-Resolver/1.0' },
      signal: AbortSignal.timeout(5000),
    });
    // 404 / 410 = truly not found; everything else means URL exists
    return res.status !== 404 && res.status !== 410;
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
  const cosZip       = `${COS_BASE}/${slug}.zip`;
  const lightmakeUrl = `https://lightmake.site/api/v1/download?slug=${slug}`;
  const clawhubUrl   = `${CLAWHUB_API}?slug=${slug}`;
  const skillsMdUrl  = `${SKILLS_SH_BASE}/${slug}/SKILL.md`;

  const [cosOk, lightmakeOk, clawhubOk, skillsMdOk] = await Promise.all([
    checkUrl(cosZip),
    checkUrl(lightmakeUrl),
    checkUrl(clawhubUrl),
    checkUrl(skillsMdUrl),
  ]);

  // Build download links (only verified sources)
  const downloadLines = [];
  if (cosOk)       downloadLines.push(`- China Mirror (SkillHub COS): ${cosZip}`);
  if (lightmakeOk) downloadLines.push(`- lightmake.site: ${lightmakeUrl}`);
  if (clawhubOk)   downloadLines.push(`- ClawHub: ${clawhubUrl}`);

  const mdLines = [];
  if (skillsMdOk)  mdLines.push(`- skills.sh / GitHub: ${skillsMdUrl}`);

  const downloadSection = downloadLines.length > 0
    ? downloadLines.join('\n')
    : '- No verified download source found. Please visit https://clawhub.ai or https://zhaojineng.com';

  const content = `# Skill: ${slug}

This is a machine-readable skill descriptor for AI agents.
Human users: visit https://zhaojineng.com to browse and download skills.

## Install Instructions

To install this skill, download the zip file and extract it to your agent's skills directory.

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
1. Download the zip from "Download Links" above (preferred), OR read the SKILL.md from "SKILL.md Sources"
2. Extract the zip to the appropriate skills directory, or save the SKILL.md as instructed
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
