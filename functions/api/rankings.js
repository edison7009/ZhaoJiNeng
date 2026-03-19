// Cloudflare Pages Function - GET /api/rankings
// Proxies clawcharts.com, extracts data from Next.js RSC payload, returns JSON
// Cached for 5 minutes to avoid excessive upstream requests

const UPSTREAM = 'https://clawcharts.com/';
const CACHE_TTL = 300; // 5 minutes

let cachedData = null;
let cachedAt = 0;

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

  // Strategy 1: Try to extract from Next.js RSC payload (self.__next_f.push)
  // Look for series data in script tags
  const seriesMatch = html.match(/"series"\s*:\s*(\[[\s\S]*?\])\s*,\s*"(?:eco|updated)/);
  if (seriesMatch) {
    try {
      const seriesData = JSON.parse(seriesMatch[1]);
      // Process series into rankings
      seriesData.forEach((item, idx) => {
        if (idx >= 10) return;
        const repo = item.repo || {};
        result.rankings.push({
          rank: idx + 1,
          name: repo.name || '',
          status: item.status || '',
          repo: repo.fullName || '',
          language: repo.language || '',
          stars7d: formatNum(item.delta7d),
          stars7dChange: formatPct(item.starsPctChange7d),
          contribs7d: String(item.contributors7d || 0),
          contribs7dChange: formatPct(item.contribsPctChange7d),
          commits7d: String(item.commits7d || 0),
          commits7dChange: formatPct(item.commitsPctChange7d),
          totalStars: formatNum(item.latestStars),
        });
      });
    } catch (e) {
      // Fall through to Strategy 2
    }
  }

  // Strategy 2: Parse plain text from the rendered HTML
  if (result.rankings.length === 0) {
    const projectNames = ['OpenClaw', 'Nanobot', 'ZeroClaw', 'PicoClaw', 'NanoClaw', 'OpenFang', 'IronClaw', 'Hermes Agent', 'NullClaw', 'TinyClaw'];

    // Get plain text version
    const text = stripTags(html);

    // Parse summary from text
    // Leader
    const leaderIdx = text.indexOf('Leader');
    if (leaderIdx !== -1) {
      const afterLeader = text.substring(leaderIdx + 6, leaderIdx + 200);
      for (const name of projectNames) {
        const nIdx = afterLeader.indexOf(name);
        if (nIdx !== -1) {
          result.summary.leader.name = name;
          const starsMatch = afterLeader.match(/([\d,]+)\s*stars/i);
          if (starsMatch) result.summary.leader.stars = starsMatch[1] + ' stars';
          break;
        }
      }
    }

    // Ecosystem Stars
    const ecoIdx = text.indexOf('Ecosystem Stars');
    if (ecoIdx !== -1) {
      const afterEco = text.substring(ecoIdx + 15, ecoIdx + 200);
      const totalMatch = afterEco.match(/([\d,]+)/);
      if (totalMatch) result.summary.ecosystemStars.total = totalMatch[1];
      const reposMatch = afterEco.match(/(Across \d+ tracked repos)/i);
      if (reposMatch) result.summary.ecosystemStars.desc = reposMatch[1];
    }

    // 7D Growth
    const growthIdx = text.indexOf('Ecosystem 7D Growth');
    if (growthIdx !== -1) {
      const afterGrowth = text.substring(growthIdx + 19, growthIdx + 200);
      const valMatch = afterGrowth.match(/(\+[\d,]+)/);
      if (valMatch) result.summary.growth7d.value = valMatch[1];
      const pctMatch = afterGrowth.match(/(Stars[\s·]*\+[\d.]+%)/i);
      if (pctMatch) result.summary.growth7d.percentage = pctMatch[1];
    }

    // Top Growth
    const topIdx = text.indexOf('Top 7D Growth');
    if (topIdx !== -1) {
      const afterTop = text.substring(topIdx + 13, topIdx + 300);
      for (const name of projectNames) {
        const nIdx = afterTop.indexOf(name);
        if (nIdx !== -1) {
          result.summary.topGrowth.name = name;
          const descMatch = afterTop.match(/(\+[\d.]+%\s*over 7 days)/i);
          if (descMatch) result.summary.topGrowth.desc = descMatch[1];
          break;
        }
      }
    }

    // Parse ranking table from text
    // Look for the table section with #1, #2... patterns
    const rankSection = text.substring(text.indexOf('#1'));
    if (rankSection) {
      for (let rank = 1; rank <= 10; rank++) {
        const startMark = `#${rank}`;
        const nextMark = rank < 10 ? `#${rank + 1}` : 'Active Contributors';
        const startIdx = rankSection.indexOf(startMark);
        if (startIdx === -1) continue;
        const endIdx = rankSection.indexOf(nextMark, startIdx + 3);
        const chunk = rankSection.substring(startIdx, endIdx > 0 ? endIdx : startIdx + 500);

        let projectName = '';
        for (const name of projectNames) {
          if (chunk.includes(name)) { projectName = name; break; }
        }
        if (!projectName) continue;

        let status = '';
        if (/RISING/i.test(chunk)) status = 'RISING';
        else if (/COOLING/i.test(chunk)) status = 'COOLING';

        const repoMatch = chunk.match(/([a-zA-Z0-9_-]+\/[a-zA-Z0-9_-]+)\s*·\s*(TypeScript|Python|Rust|Go|Zig)/i);
        const repo = repoMatch ? repoMatch[1] : '';
        const language = repoMatch ? repoMatch[2] : '';

        // Extract numeric data from the chunk
        // Remove project name, repo path, and language to isolate stats
        let statsText = chunk;
        statsText = statsText.replace(startMark, '');
        statsText = statsText.replace(projectName, '');
        if (repo) statsText = statsText.replace(repo, '');
        if (language) statsText = statsText.replace(language, '');
        statsText = statsText.replace(/RISING|COOLING|·/gi, '');

        const nums = [];
        const numRegex = /[+-]?[\d,]+(?:\.[\d]+)?(?:%)?/g;
        let m;
        while ((m = numRegex.exec(statsText)) !== null) {
          const v = m[0].trim();
          if (v && v !== String(rank) && v.length > 0) nums.push(v);
        }

        result.rankings.push({
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
        });
      }
    }
  }

  // Fill summary from rankings if not parsed from text
  if (!result.summary.leader.name && result.rankings.length > 0) {
    result.summary.leader.name = result.rankings[0].name;
    result.summary.leader.stars = result.rankings[0].totalStars + ' stars';
  }

  return result;
}

function formatNum(n) {
  if (n === undefined || n === null) return '0';
  return Number(n).toLocaleString('en-US');
}

function formatPct(n) {
  if (n === undefined || n === null) return '0%';
  return (n >= 0 ? '+' : '') + Number(n).toFixed(1) + '%';
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
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml',
        'Accept-Language': 'en-US,en;q=0.9',
        'Referer': 'https://www.google.com/',
      },
      signal: AbortSignal.timeout(15000),
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
