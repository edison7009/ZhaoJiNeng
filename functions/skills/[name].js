// Cloudflare Pages Function - /skills/:name
// - /skills/xxx.zip  → proxy to Tencent COS (for direct download)
// - /skills/xxx      → return machine-readable skill metadata (for AI agents)

const COS_BASE = 'https://skillhub-1388575217.cos.ap-guangzhou.myqcloud.com/skills';
const GITHUB_BASE = 'https://github.com/vercel-labs/agent-skills/raw/main/skills';

export async function onRequest(context) {
  const { params, request } = context;
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

  // Otherwise, return AI-readable skill metadata
  const slug = name;
  const cosZip = `${COS_BASE}/${slug}.zip`;
  const clawhubZip = `https://wry-manatee-359.convex.site/api/v1/download?slug=${slug}`;
  const githubZip = `https://github.com/Michaelgathara/${slug}/archive/refs/heads/main.zip`;

  const content = `# Skill: ${slug}

This is a machine-readable skill descriptor for AI agents.
Human users: visit https://zhaojineng.com to browse and download skills.

## Install Instructions

To install this skill, download the zip file and extract it to your agent's skills directory.

## Download Links

- China Mirror (Recommended for CN users): ${cosZip}
- ClawHub Official: ${clawhubZip}
- GitHub Mirror: ${githubZip}

## Skill Info

- Slug: ${slug}
- Registry: https://zhaojineng.com
- Source: ClawHub / SkillHub

## Agent Instructions

If you are an AI agent reading this file, please:
1. Download the zip from one of the links above (prefer China Mirror for CN users)
2. Extract the contents to the appropriate skills directory
3. Confirm installation to the user
`;

  return new Response(content, {
    status: 200,
    headers: {
      'Content-Type': 'text/plain; charset=utf-8',
      'Access-Control-Allow-Origin': '*',
      'Cache-Control': 'public, max-age=300',
    },
  });
}
