// Cloudflare Pages Function - GET /api/rankings
// Proxies clawcharts.com HTML, parses SSR data, returns structured JSON
// Cached for 5 minutes to avoid excessive upstream requests

const UPSTREAM = 'https://clawcharts.com/';
const CACHE_TTL = 300; // 5 minutes

let cachedData = null;
let cachedAt = 0;

function extractText(html, startMark, endMark) {
  const i = html.indexOf(startMark);
  if (i === -1) return '';
  const begin = i + startMark.length;
  const end = html.indexOf(endMark, begin);
  if (end === -1) return '';
  return html.substring(begin, end).trim();
}

function stripTags(s) {
  return s.replace(/<[^>]*>/g, '').trim();
}

function parseRankingData(html) {
  const result = {
    updatedAt: new Date().toISOString(),
    summary: {
      leader: { name: '', stars: '' },
      ecosystemStars: { total: '', desc: '' },
      growth7d: { value: '', percentage: '' },
      topGrowth: { name: '', desc: '' },
    },
    rankings: [],
  };

  // --- Summary cards parsing ---
  // Leader
  const leaderMatch = html.match(/LEADER[\s\S]*?<[^>]*>([A-Za-z][A-Za-z0-9 ]*?)<\/[^>]*>[\s\S]*?([\d,]+ stars)/i);
  if (leaderMatch) {
    result.summary.leader.name = leaderMatch[1].trim();
    result.summary.leader.stars = leaderMatch[2].trim();
  }

  // Ecosystem Stars
  const ecoMatch = html.match(/ECOSYSTEM STARS[\s\S]*?>([\d,]+)<[\s\S]*?>(Across \d+ tracked repos)/i);
  if (ecoMatch) {
    result.summary.ecosystemStars.total = ecoMatch[1].trim();
    result.summary.ecosystemStars.desc = ecoMatch[2].trim();
  }

  // Ecosystem 7D Growth
  const growthMatch = html.match(/ECOSYSTEM 7D GROWTH[\s\S]*?>(\+[\d,]+)<[\s\S]*?>(Stars[\s·]*\+[\d.]+%)/i);
  if (growthMatch) {
    result.summary.growth7d.value = growthMatch[1].trim();
    result.summary.growth7d.percentage = growthMatch[2].trim();
  }

  // Top 7D Growth
  const topMatch = html.match(/TOP 7D GROWTH[\s\S]*?<[^>]*>([A-Za-z][A-Za-z0-9 ]*?)<\/[^>]*>[\s\S]*?(\+[\d.]+% over 7 days)/i);
  if (topMatch) {
    result.summary.topGrowth.name = topMatch[1].trim();
    result.summary.topGrowth.desc = topMatch[2].trim();
  }

  // --- Ranking rows parsing ---
  // Each row: #N, ProjectName, status(RISING/COOLING), repo/path, Language, 7D Stars, % change, 7D contribs, % change, 7D commits, % change, total stars
  const rowRegex = /#(\d+)[\s\S]*?<[^>]*?>((?:OpenClaw|Nanobot|ZeroClaw|PicoClaw|NanoClaw|OpenFang|IronClaw|Hermes Agent|NullClaw|TinyClaw)[^<]*)<\/[^>]*>/gi;
  const rows = html.matchAll(rowRegex);

  // More robust: split into table-row-like chunks
  const projectNames = ['OpenClaw', 'Nanobot', 'ZeroClaw', 'PicoClaw', 'NanoClaw', 'OpenFang', 'IronClaw', 'Hermes Agent', 'NullClaw', 'TinyClaw'];

  // Extract all numbers that appear in the table area
  const tableArea = html.substring(html.indexOf('RANK'));
  if (!tableArea) return result;

  for (let rank = 1; rank <= 10; rank++) {
    const startMark = `#${rank}`;
    const endMark = rank < 10 ? `#${rank + 1}` : 'Active Contributors';
    const startIdx = tableArea.indexOf(startMark);
    if (startIdx === -1) continue;
    const endIdx = rank < 10 ? tableArea.indexOf(endMark, startIdx + 3) : tableArea.indexOf('</section', startIdx);
    if (endIdx === -1) continue;

    const chunk = tableArea.substring(startIdx, endIdx > 0 ? endIdx : undefined);

    // Extract project name
    let projectName = '';
    for (const name of projectNames) {
      if (chunk.includes(name)) { projectName = name; break; }
    }
    if (!projectName) continue;

    // Status badge
    let status = '';
    if (/RISING/i.test(chunk)) status = 'RISING';
    else if (/COOLING/i.test(chunk)) status = 'COOLING';

    // Repo path (e.g., openclaw/openclaw)
    const repoMatch = chunk.match(/([a-zA-Z0-9_-]+\/[a-zA-Z0-9_-]+)\s*·\s*(TypeScript|Python|Rust|Go|Zig)/i);
    const repo = repoMatch ? repoMatch[1] : '';
    const language = repoMatch ? repoMatch[2] : '';

    // Extract numbers: look for patterns like +17,366 or 120 or +5.6% or 25.9%
    const nums = [];
    const numRegex = /[+]?[\d,]+(?:\.[\d]+)?(?:%)?/g;
    const plainChunk = stripTags(chunk);
    let m;
    while ((m = numRegex.exec(plainChunk)) !== null) {
      const v = m[0];
      // Skip the rank number itself
      if (v === String(rank)) continue;
      nums.push(v);
    }

    // Typical order in the row: 7dStars, %change, 7dContribs, %change, 7dCommits, %change, totalStars
    const entry = {
      rank,
      name: projectName,
      status,
      repo,
      language,
      stars7d: nums[0] || '0',
      stars7dChange: nums[1] || '0%',
      contribs7d: nums[2] || '0',
      contribs7dChange: nums[3] || '0%',
      commits7d: nums[4] || '0',
      commits7dChange: nums[5] || '0%',
      totalStars: nums[6] || '0',
    };

    result.rankings.push(entry);
  }

  return result;
}

export async function onRequest(context) {
  const now = Date.now();

  // Check cache
  if (cachedData && (now - cachedAt) < CACHE_TTL * 1000) {
    return new Response(JSON.stringify(cachedData), {
      status: 200,
      headers: {
        'Content-Type': 'application/json',
        'Access-Control-Allow-Origin': '*',
        'Cache-Control': `public, max-age=${CACHE_TTL}`,
        'X-Data-Source': 'cache',
      },
    });
  }

  try {
    const res = await fetch(UPSTREAM, {
      headers: {
        'User-Agent': 'ZhaoJiNeng-Ranking/1.0 (zhaojineng.com)',
        'Accept': 'text/html',
      },
      signal: AbortSignal.timeout(10000),
    });

    if (!res.ok) throw new Error(`Upstream ${res.status}`);

    const html = await res.text();
    const data = parseRankingData(html);

    cachedData = data;
    cachedAt = now;

    return new Response(JSON.stringify(data), {
      status: 200,
      headers: {
        'Content-Type': 'application/json',
        'Access-Control-Allow-Origin': '*',
        'Cache-Control': `public, max-age=${CACHE_TTL}`,
        'X-Data-Source': 'fresh',
      },
    });
  } catch (err) {
    // Return cached data if available, else error
    if (cachedData) {
      return new Response(JSON.stringify(cachedData), {
        status: 200,
        headers: {
          'Content-Type': 'application/json',
          'Access-Control-Allow-Origin': '*',
          'X-Data-Source': 'stale-cache',
        },
      });
    }

    return new Response(JSON.stringify({ error: err.message }), {
      status: 502,
      headers: {
        'Content-Type': 'application/json',
        'Access-Control-Allow-Origin': '*',
      },
    });
  }
}
