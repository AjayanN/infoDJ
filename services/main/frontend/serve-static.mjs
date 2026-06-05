import { createReadStream, existsSync, statSync } from 'node:fs';
import { createServer } from 'node:http';
import { extname, join, normalize } from 'node:path';

const root = join(process.cwd(), 'dist', 'infodj-main-frontend', 'browser');
const port = Number(process.env.PORT || 4200);
const host = process.env.HOST || '0.0.0.0';

const contentTypes = {
  '.css': 'text/css; charset=utf-8',
  '.html': 'text/html; charset=utf-8',
  '.js': 'text/javascript; charset=utf-8',
  '.json': 'application/json; charset=utf-8',
  '.svg': 'image/svg+xml',
  '.txt': 'text/plain; charset=utf-8',
};

createServer((request, response) => {
  const url = new URL(request.url || '/', `http://${request.headers.host || 'localhost'}`);
  const requestedPath = normalize(decodeURIComponent(url.pathname)).replace(/^(\.\.[/\\])+/, '');
  let filePath = join(root, requestedPath);

  if (!existsSync(filePath) || statSync(filePath).isDirectory()) {
    filePath = join(root, 'index.html');
  }

  response.setHeader('Cache-Control', 'no-cache');
  response.setHeader('Content-Type', contentTypes[extname(filePath)] || 'application/octet-stream');
  createReadStream(filePath)
    .on('error', () => {
      response.statusCode = 404;
      response.end('Not found');
    })
    .pipe(response);
}).listen(port, host, () => {
  console.log(`InfoDJ frontend available at http://${host}:${port}/`);
});
