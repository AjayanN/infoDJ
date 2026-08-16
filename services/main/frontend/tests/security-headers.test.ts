import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import test from 'node:test';

const root = new URL('..', import.meta.url);

test('public frontend sends browser security headers', () => {
  const server = readFileSync(new URL('serve-static.mjs', root), 'utf8');
  const application = readFileSync(new URL('src/main.ts', root), 'utf8');

  assert.match(server, /Content-Security-Policy/);
  assert.match(server, /X-Content-Type-Options/);
  assert.match(server, /X-Frame-Options/);
  assert.match(server, /Referrer-Policy/);
  assert.match(application, /url\.hash\.replace/);
});
