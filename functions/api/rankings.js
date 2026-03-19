// Cloudflare Pages Function - GET /api/rankings
// Extracts data from clawcharts.com Next.js RSC payload
// Cached for 5 minutes

const UPSTREAM = 'https://clawcharts.com/';
const CACHE_TTL = 300;

let cachedData = null;
let cachedAt = 0;

function fmt(n) {
  if (n === undefined || n === null) return '0';
  return Number(n).toLocaleString('en-US');
}

function fmtPct(n) {
  if (n === undefined || n === null) return '0%';
  const v = Number(n);
  return (v >= 0 ? '+' : '') + v.toFixed(1) + '%';
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

  // ---- Strategy 1: Extract from RSC script payload (most reliable) ----
  // The RSC payload contains escaped JSON like: \"latestStars\":325002,\"delta7d\":17430
  // Find project data blocks in the RSC payload

  const projectNames = ['OpenClaw', 'Nanobot', 'ZeroClaw', 'PicoClaw', 'NanoClaw', 'OpenFang', 'IronClaw', 'Hermes Agent', 'NullClaw', 'TinyClaw'];
  const projectRepos = {
    'OpenClaw': 'openclaw/openclaw',
    'Nanobot': 'HKUDS/nanobot',
    'ZeroClaw': 'zeroclaw-labs/zeroclaw',
    'PicoClaw': 'sipeed/picoclaw',
    'NanoClaw': 'qwibitai/nanoclaw',
    'OpenFang': 'RightNow-AI/openfang',
    'IronClaw': 'nearai/ironclaw',
    'Hermes Agent': 'NousResearch/hermes-agent',
    'NullClaw': 'nullclaw/nullclaw',
    'TinyClaw': 'TinyAGI/tinyclaw',
  };

  // Try to extract latestStars and delta7d from RSC payload
  const latestStarsRegex = /\\?"latestStars\\?"\s*:\s*(\d+)/g;
  const delta7dRegex = /\\?"delta7d\\?"\s*:\s*(-?\d+)/g;
  const nameRegex = /\\?"name\\?"\s*:\s*\\?"([^"\\]+)\\?"/g;

  const names = [];
  const stars = [];
  const deltas = [];

  let m;
  while ((m = nameRegex.exec(html)) !== null) {
    const n = m[1];
    if (projectNames.includes(n)) names.push({ name: n, pos: m.index });
  }
  while ((m = latestStarsRegex.exec(html)) !== null) {
    stars.push({ val: parseInt(m[1]), pos: m.index });
  }
  while ((m = delta7dRegex.exec(html)) !== null) {
    deltas.push({ val: parseInt(m[1]), pos: m.index });
  }

  // Also try to extract percentage changes and contributor/commit data
  const starsPctRegex = /\\?"starsPctChange7d\\?"\s*:\s*(-?[\d.]+)/g;
  const contribs7dRegex = /\\?"contributors7d\\?"\s*:\s*(\d+)/g;
  const contribsPctRegex = /\\?"contribsPctChange7d\\?"\s*:\s*(-?[\d.]+)/g;
  const commits7dRegex = /\\?"commits7d\\?"\s*:\s*(\d+)/g;
  const commitsPctRegex = /\\?"commitsPctChange7d\\?"\s*:\s*(-?[\d.]+)/g;
  const statusRegex = /\\?"status\\?"\s*:\s*\\?"(RISING|COOLING|)\\?"/g;

  const starsPcts = [];
  const contribs = [];
  const contribsPcts = [];
  const commits = [];
  const commitsPcts = [];
  const statuses = [];

  while ((m = starsPctRegex.exec(html)) !== null) starsPcts.push(parseFloat(m[1]));
  while ((m = contribs7dRegex.exec(html)) !== null) contribs.push(parseInt(m[1]));
  while ((m = contribsPctRegex.exec(html)) !== null) contribsPcts.push(parseFloat(m[1]));
  while ((m = commits7dRegex.exec(html)) !== null) commits.push(parseInt(m[1]));
  while ((m = commitsPctRegex.exec(html)) !== null) commitsPcts.push(parseFloat(m[1]));
  while ((m = statusRegex.exec(html)) !== null) statuses.push(m[1]);

  if (names.length >= 10 && stars.length >= 10 && deltas.length >= 10) {
    // Build rankings from RSC data
    for (let i = 0; i < Math.min(names.length, 10); i++) {
      const name = names[i].name;
      result.rankings.push({
        rank: i + 1,
        name,
        status: statuses[i] || '',
        repo: projectRepos[name] || '',
        language: '',
        stars7d: '+' + fmt(deltas[i]?.val),
        stars7dChange: fmtPct(starsPcts[i]),
        contribs7d: String(contribs[i] || 0),
        contribs7dChange: fmtPct(contribsPcts[i]),
        commits7d: fmt(commits[i] || 0),
        commits7dChange: fmtPct(commitsPcts[i]),
        totalStars: fmt(stars[i]?.val),
      });
    }
  }

  // ---- Parse summary from plain text ----
  const text = html.replace(/<[^>]*>/g, '').trim();

  // Leader
  const leaderIdx = text.indexOf('Leader');
  if (leaderIdx !== -1) {
    const after = text.substring(leaderIdx, leaderIdx + 200);
    for (const name of projectNames) {
      if (after.includes(name)) {
        result.summary.leader.name = name;
        const sm = after.match(/([\d,]+)\s*stars/i);
        if (sm) result.summary.leader.stars = sm[1] + ' stars';
        break;
      }
    }
  }

  // Ecosystem Stars
  const ecoIdx = text.indexOf('Ecosystem Stars');
  if (ecoIdx !== -1) {
    const after = text.substring(ecoIdx + 15, ecoIdx + 200);
    const tm = after.match(/([\d,]+)/);
    if (tm) result.summary.ecosystemStars.total = tm[1];
    const rm = after.match(/(Across \d+ tracked repos)/i);
    if (rm) result.summary.ecosystemStars.desc = rm[1];
  }

  // 7D Growth
  const growthIdx = text.indexOf('Ecosystem 7D Growth');
  if (growthIdx !== -1) {
    const after = text.substring(growthIdx + 19, growthIdx + 200);
    const vm = after.match(/(\+[\d,]+)/);
    if (vm) result.summary.growth7d.value = vm[1];
    const pm = after.match(/(Stars[\s·]*\+[\d.]+%)/i);
    if (pm) result.summary.growth7d.percentage = pm[1];
  }

  // Top Growth
  const topIdx = text.indexOf('Top 7D Growth');
  if (topIdx !== -1) {
    const after = text.substring(topIdx + 13, topIdx + 300);
    for (const name of projectNames) {
      if (after.includes(name)) {
        result.summary.topGrowth.name = name;
        const dm = after.match(/(\+[\d.]+%\s*over 7 days)/i);
        if (dm) result.summary.topGrowth.desc = dm[1];
        break;
      }
    }
  }

  // Fill summary leader from rankings if needed
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

    // Only cache if we got meaningful data
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
