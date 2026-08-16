import { createReadStream, existsSync, statSync } from 'node:fs';
import { createServer, request as proxyRequest } from 'node:http';
import { extname, join, normalize } from 'node:path';

const root = join(process.cwd(), 'dist', 'infodj-main-frontend', 'browser');
const port = Number(process.env.PORT || 4200);
const host = process.env.HOST || '0.0.0.0';
const apiGateway = process.env.API_GATEWAY_URL || 'http://gateway:8000';

const contentTypes = {
  '.css': 'text/css; charset=utf-8',
  '.html': 'text/html; charset=utf-8',
  '.js': 'text/javascript; charset=utf-8',
  '.json': 'application/json; charset=utf-8',
  '.svg': 'image/svg+xml',
  '.txt': 'text/plain; charset=utf-8',
};

function proxyApi(request, response) {
  const target = new URL(request.url || '/', apiGateway);
  const upstream = proxyRequest(target, {
    method: request.method,
    headers: { ...request.headers, host: target.host },
  }, (upstreamResponse) => {
    response.writeHead(upstreamResponse.statusCode || 502, upstreamResponse.headers);
    upstreamResponse.pipe(response);
  });
  upstream.on('error', () => {
    response.statusCode = 502;
    response.setHeader('Content-Type', 'application/json; charset=utf-8');
    response.end(JSON.stringify({ detail: 'InfoDJ API is temporarily unavailable.' }));
  });
  request.pipe(upstream);
}

createServer((request, response) => {
  const url = new URL(request.url || '/', 'http://' + (request.headers.host || 'localhost'));
  if (url.pathname.startsWith('/api/app/')) {
    proxyApi(request, response);
    return;
  }

  const requestedPath = normalize(decodeURIComponent(url.pathname)).replace(/^(\.\.[/\\])+/, '');
  let filePath = join(root, requestedPath);
  if (!existsSync(filePath) || statSync(filePath).isDirectory()) {
    filePath = join(root, 'index.html');
  }

  response.setHeader('Cache-Control', 'no-cache');
  response.setHeader('Content-Type', contentTypes[extname(filePath)] || 'application/octet-stream');
  response.setHeader('Content-Security-Policy', "default-src 'self'; base-uri 'self'; connect-src 'self'; font-src 'self' data:; frame-ancestors 'none'; form-action 'self'; img-src 'self' data:; object-src 'none'; script-src 'self' https://checkout.razorpay.com; style-src 'self' 'unsafe-inline'");
  response.setHeader('Permissions-Policy', 'camera=(), geolocation=(), microphone=()');
  response.setHeader('Referrer-Policy', 'no-referrer');
  response.setHeader('X-Content-Type-Options', 'nosniff');
  response.setHeader('X-Frame-Options', 'DENY');
  createReadStream(filePath)
    .on('error', () => {
      response.statusCode = 404;
      response.end('Not found');
    })
    .pipe(response);
}).listen(port, host, () => {
  console.log('InfoDJ frontend available at http://' + host + ':' + port + '/');
});
