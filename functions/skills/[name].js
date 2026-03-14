// Cloudflare Pages Function
// Proxies /skills/:name -> Tencent COS mirror
// So https://zhaojineng.com/skills/xxx.zip -> COS/skills/xxx.zip

export async function onRequest(context) {
  const { params } = context;
  const name = params.name;
  const cosUrl = `https://skillhub-1388575217.cos.ap-guangzhou.myqcloud.com/skills/${name}`;

  const response = await fetch(cosUrl, {
    headers: {
      'User-Agent': 'ZhaoJiNeng-Proxy/1.0',
    },
  });

  // Pass through the response with CORS headers
  const newHeaders = new Headers(response.headers);
  newHeaders.set('Access-Control-Allow-Origin', '*');
  newHeaders.set('Cache-Control', 'public, max-age=3600');

  return new Response(response.body, {
    status: response.status,
    headers: newHeaders,
  });
}
