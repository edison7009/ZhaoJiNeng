// Cloudflare Pages Function - GET /api/rankings
// Hybrid parsing: RSC payload for stars + HTML table for details
// Cached for 5 minutes

const UPSTREAM = 'https://clawcharts.com/';
const CACHE_TTL = 300;

let cachedData = null;
let cachedAt = 0;

function fmt(n) {
  if (n === undefined || n === null) return '0';
  return Number(n).toLocaleString('en-US');
}

const PROJECT_NAMES = ['OpenClaw', 'Nanobot', 'ZeroClaw', 'PicoClaw', 'NanoClaw', 'OpenFang', 'IronClaw', 'Hermes Agent', 'NullClaw', 'TinyClaw'];
const PROJECT_REPOS = {
  'OpenClaw': 'openclaw/openclaw', 'Nanobot': 'HKUDS/nanobot',
  'ZeroClaw': 'zeroclaw-labs/zeroclaw', 'PicoClaw': 'sipeed/picoclaw',
  'NanoClaw': 'qwibitai/nanoclaw', 'OpenFang': 'RightNow-AI/openfang',
  'IronClaw': 'nearai/ironclaw', 'Hermes Agent': 'NousResearch/hermes-agent',
  'NullClaw': 'nullclaw/nullclaw', 'TinyClaw': 'TinyAGI/tinyclaw',
};

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

  // ---- Step 1: Get stars data from RSC payload (reliable) ----
  const rscNames = [];
  const rscStars = [];
  const rscDeltas = [];

  const nameRx = /\\?"name\\?"\s*:\s*\\?"([^"\\]+)\\?"/g;
  const starsRx = /\\?"latestStars\\?"\s*:\s*(\d+)/g;
  const deltaRx = /\\?"delta7d\\?"\s*:\s*(-?\d+)/g;

  let m;
  while ((m = nameRx.exec(html)) !== null) {
    if (PROJECT_NAMES.includes(m[1])) rscNames.push(m[1]);
  }
  while ((m = starsRx.exec(html)) !== null) rscStars.push(parseInt(m[1]));
  while ((m = deltaRx.exec(html)) !== null) rscDeltas.push(parseInt(m[1]));

  // ---- Step 2: Parse HTML table rows for detailed data ----
  // Each project appears in an <a> tag with its GitHub URL, followed by data cells
  // We split the HTML by project anchors to isolate each row's data

  const rowData = {};
  for (let i = 0; i < PROJECT_NAMES.length; i++) {
    const name = PROJECT_NAMES[i];
    rowData[name] = {
      status: '',
      stars7dPct: '0%',
      contribs7d: '0',
      contribs7dPct: '0%',
      commits7d: '0',
      commits7dPct: '0%',
    };

    // Find the project's section in the HTML by looking for its GitHub link
    const repo = PROJECT_REPOS[name];
    const repoIdx = html.indexOf(`github.com/${repo}`);
    if (repoIdx === -1) continue;

    // Get a chunk after the repo link - this contains the row data
    // Look for the next project or end of table
    let endIdx = html.length;
    for (let j = i + 1; j < PROJECT_NAMES.length; j++) {
      const nextRepo = PROJECT_REPOS[PROJECT_NAMES[j]];
      const nextIdx = html.indexOf(`github.com/${nextRepo}`, repoIdx + 50);
      if (nextIdx > -1) { endIdx = nextIdx; break; }
    }
    const chunk = html.substring(repoIdx, endIdx);

    // Status: Rising or Cooling
    if (/Rising/i.test(chunk)) rowData[name].status = 'RISING';
    else if (/Cooling/i.test(chunk)) rowData[name].status = 'COOLING';

    // Extract all numbers with optional +/- and % from the chunk
    // Strip HTML tags first
    const text = chunk.replace(/<[^>]*>/g, ' ').replace(/\s+/g, ' ');

    // Find percentage values (e.g., +5.7%, 25.9%, +88.1%)
    const pcts = [];
    const pctRx = /([+-]?[\d.]+%)/g;
    while ((m = pctRx.exec(text)) !== null) pcts.push(m[1]);

    // Find plain numbers (contributor/commit counts)
    // These appear after the project repo info
    const langIdx = text.indexOf('TypeScript') > -1 ? text.indexOf('TypeScript') :
      text.indexOf('Python') > -1 ? text.indexOf('Python') :
      text.indexOf('Rust') > -1 ? text.indexOf('Rust') :
      text.indexOf('Go ') > -1 ? text.indexOf('Go ') :
      text.indexOf('Zig') > -1 ? text.indexOf('Zig') : 0;

    const afterLang = text.substring(langIdx);
    const nums = [];
    const numRx = /(?:^|\s)([+-]?[\d,]+)(?:\s|$)/g;
    while ((m = numRx.exec(afterLang)) !== null) {
      const v = m[1].replace(/,/g, '');
      if (v && parseInt(v) !== 0) nums.push(m[1]);
    }

    // Map extracted data:
    // pcts order: stars7dPct, contribs7dPct, commits7dPct
    if (pcts[0]) rowData[name].stars7dPct = pcts[0].startsWith('+') || pcts[0].startsWith('-') ? pcts[0] : '+' + pcts[0];
    if (pcts[1]) rowData[name].contribs7dPct = pcts[1];
    if (pcts[2]) rowData[name].commits7dPct = pcts[2];

    // nums: stars7d (skip, from RSC), contribs count, commits count, total stars (skip, from RSC)
    if (nums.length >= 2) {
      rowData[name].contribs7d = nums[0];
      rowData[name].commits7d = nums[1];
    }
  }

  // ---- Step 3: Build rankings ----
  const hasRsc = rscNames.length >= 10 && rscStars.length >= 10;

  for (let i = 0; i < (hasRsc ? rscNames.length : PROJECT_NAMES.length); i++) {
    const name = hasRsc ? rscNames[i] : PROJECT_NAMES[i];
    const rd = rowData[name] || {};

    result.rankings.push({
      rank: i + 1,
      name,
      status: rd.status || '',
      repo: PROJECT_REPOS[name] || '',
      language: '',
      stars7d: hasRsc ? '+' + fmt(rscDeltas[i]) : '0',
      stars7dChange: rd.stars7dPct || '0%',
      contribs7d: rd.contribs7d || '0',
      contribs7dChange: rd.contribs7dPct || '0%',
      commits7d: rd.commits7d || '0',
      commits7dChange: rd.commits7dPct || '0%',
      totalStars: hasRsc ? fmt(rscStars[i]) : '0',
    });
  }

  // ---- Step 4: Parse summary from text ----
  const text = html.replace(/<[^>]*>/g, '');

  const leaderIdx = text.indexOf('Leader');
  if (leaderIdx !== -1) {
    const after = text.substring(leaderIdx, leaderIdx + 200);
    for (const name of PROJECT_NAMES) {
      if (after.includes(name)) {
        result.summary.leader.name = name;
        const sm = after.match(/([\d,]+)\s*stars/i);
        if (sm) result.summary.leader.stars = sm[1] + ' stars';
        break;
      }
    }
  }

  const ecoIdx = text.indexOf('Ecosystem Stars');
  if (ecoIdx !== -1) {
    const after = text.substring(ecoIdx + 15, ecoIdx + 200);
    const tm = after.match(/([\d,]+)/);
    if (tm) result.summary.ecosystemStars.total = tm[1];
    const rm = after.match(/(Across \d+ tracked repos)/i);
    if (rm) result.summary.ecosystemStars.desc = rm[1];
  }

  const growthIdx = text.indexOf('Ecosystem 7D Growth');
  if (growthIdx !== -1) {
    const after = text.substring(growthIdx + 19, growthIdx + 200);
    const vm = after.match(/(\+[\d,]+)/);
    if (vm) result.summary.growth7d.value = vm[1];
    const pm = after.match(/(Stars[\s·]*\+[\d.]+%)/i);
    if (pm) result.summary.growth7d.percentage = pm[1];
  }

  const topIdx = text.indexOf('Top 7D Growth');
  if (topIdx !== -1) {
    const after = text.substring(topIdx + 13, topIdx + 300);
    for (const name of PROJECT_NAMES) {
      if (after.includes(name)) {
        result.summary.topGrowth.name = name;
        const dm = after.match(/(\+[\d.]+%\s*over 7 days)/i);
        if (dm) result.summary.topGrowth.desc = dm[1];
        break;
      }
    }
  }

  if (!result.summary.leader.name && result.rankings.length > 0) {
    result.summary.leader.name = result.rankings[0].name;
    result.summary.leader.stars = result.rankings[0].totalStars + ' stars';
  }

  return result;
}

export async function onRequest(context) {
  const now = Date.now();

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
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml',
        'Accept-Language': 'en-US,en;q=0.9',
      },
      signal: AbortSignal.timeout(15000),
    });

    if (!res.ok) throw new Error(`Upstream ${res.status}`);

    const html = await res.text();
    const data = parseRankingData(html);

    if (data.rankings.length >= 5) {
      cachedData = data;
      cachedAt = now;
    }

    return new Response(JSON.stringify(data), {
      status: 200,
      headers: {
        'Content-Type': 'application/json',
        'Access-Control-Allow-Origin': '*',
        'Cache-Control': `public, max-age=${CACHE_TTL}`,
        'X-Data-Source': 'fresh',
        'X-Rankings-Count': String(data.rankings.length),
      },
    });
  } catch (err) {
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
