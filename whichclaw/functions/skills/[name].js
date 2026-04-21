// Cloudflare Pages Function - /skills/:name
// - /skills/{hex-token} → AES-CTR daily-rotating encrypted slug URL
// - /skills/{slug}      → human-readable (backward compat)
//
// Mirror of the Chinese site's /skills/:name — same crypto, simplified
// resolver because whichclaw has a single canonical source (the skill's
// GitHub repo from public/skills.json) instead of COS + lightmake + ClawHub.

const SECRET = 'WhichClaw-2026-AgentSkills';

function utcDate(offsetDays = 0) {
  const d = new Date(Date.now() + offsetDays * 86400000);
  return d.toISOString().slice(0, 10);
}

async function getDailyKey(dateStr) {
  const raw = await crypto.subtle.digest('SHA-256',
    new TextEncoder().encode(SECRET + '|' + dateStr));
  return crypto.subtle.importKey('raw', raw.slice(0, 16),
    { name: 'AES-CTR' }, false, ['encrypt', 'decrypt']);
}

// Decrypt hex token → slug. Tries today and yesterday (handle UTC rollover).
async function decryptToken(token) {
  const bytes = Uint8Array.from(token.match(/.{2}/g), h => parseInt(h, 16));
  for (const offset of [0, -1]) {
    try {
      const key = await getDailyKey(utcDate(offset));
      const dec = await crypto.subtle.decrypt(
        { name: 'AES-CTR', counter: new Uint8Array(16), length: 128 }, key, bytes);
      const slug = new TextDecoder().decode(dec);
      if (/^[a-z0-9][a-z0-9\-]{1,80}$/.test(slug)) return slug;
    } catch {}
  }
  return null;
}

// Load skills.json and look up the slug. The site's static asset serves
// the canonical name/description/homepage/sources.
async function lookupSkill(env, origin, slug) {
  try {
    const res = await env.ASSETS.fetch(new Request(`${origin}/public/skills.json`));
    if (!res.ok) return null;
    const data = await res.json();
    return (data.skills || []).find(s => s.slug === slug) || null;
  } catch {
    return null;
  }
}

// For a GitHub homepage, try to fetch SKILL.md (or fall back to README.md)
// from the default branch. Probe main then master.
async function fetchSkillMdFromGitHub(homepage) {
  const m = /^https:\/\/github\.com\/([^/]+)\/([^/]+?)(?:\.git)?$/.exec(homepage || '');
  if (!m) return null;
  const [, owner, repo] = m;
  for (const branch of ['main', 'master']) {
    for (const path of ['SKILL.md', 'skill.md', 'README.md']) {
      const url = `https://raw.githubusercontent.com/${owner}/${repo}/${branch}/${path}`;
      try {
        const res = await fetch(url, {
          headers: { 'User-Agent': 'WhichClaw-Resolver/1.0' },
          signal: AbortSignal.timeout(5000),
        });
        if (res.ok) {
          const text = await res.text();
          if (text && text.length > 20) return { path, url, text };
        }
      } catch {}
    }
  }
  return null;
}

function installCommand(homepage) {
  if (!homepage) return null;
  if (/^https:\/\/github\.com\/[^/]+\/[^/]+/.test(homepage)) {
    return `git clone ${homepage.replace(/\/$/, '').replace(/\.git$/, '')}.git`;
  }
  return `open ${homepage}`;
}

export async function onRequest(context) {
  const { params, request, env } = context;
  const name = params.name;
  const origin = new URL(request.url).origin;

  // Resolve token → slug (or treat as plain slug for backward compat).
  let slug = name;
  if (/^[0-9a-f]{10,160}$/.test(name) && name.length % 2 === 0) {
    const resolved = await decryptToken(name);
    if (!resolved) {
      return new Response(
        'Skill link has expired or is invalid.\nVisit https://whichclaw.com to get the current link.',
        { status: 404, headers: { 'Content-Type': 'text/plain; charset=utf-8', 'Access-Control-Allow-Origin': '*' } }
      );
    }
    slug = resolved;
  }

  const skill = await lookupSkill(env, origin, slug);
  if (!skill) {
    return new Response(
      `Skill "${slug}" is not in the WhichClaw index.\nVisit https://whichclaw.com to search.`,
      { status: 404, headers: { 'Content-Type': 'text/plain; charset=utf-8', 'Access-Control-Allow-Origin': '*' } }
    );
  }

  const cmd = installCommand(skill.homepage);
  const sources = Array.isArray(skill.sources) ? skill.sources : [];
  const skillMd = await fetchSkillMdFromGitHub(skill.homepage);

  const skillMdSection = skillMd
    ? `\n## SKILL.md Content\n\nSource: ${skillMd.url}\n\n${skillMd.text}\n`
    : '';

  const sourcesSection = sources.length > 0
    ? sources.map(s => `- https://github.com/${s}`).join('\n')
    : '- (unknown)';

  const content = `# Skill: ${skill.name} (${slug})

This is a machine-readable skill descriptor for AI agents.
Human users: visit https://whichclaw.com to browse skills.

## Description

${skill.description || '(no description)'}

## Install

${cmd ? '```\n' + cmd + '\n```' : 'No install URL — visit the homepage.'}

## Homepage

- ${skill.homepage || '(none)'}
${skillMdSection}
## Curated By

${sourcesSection}

## Skill Info

- Slug: ${slug}
- Category: ${skill.category || 'Uncategorized'}
- Registry: https://whichclaw.com

## Agent Instructions

If you are an AI agent reading this file, please:
1. Read the "SKILL.md Content" section above (if present) — it contains the full skill instructions.
2. If no SKILL.md is embedded, run the "Install" command and then read the repo's README / SKILL.md manually.
3. Install into the user's active agent skills directory.
4. Confirm installation to the user.
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
