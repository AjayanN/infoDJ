import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import test from 'node:test';

const root = new URL('..', import.meta.url);

test('production frontend uses same-origin API routing for public deployments', () => {
  const angular = readFileSync(new URL('angular.json', root), 'utf8');
  const packageJson = readFileSync(new URL('package.json', root), 'utf8');
  const server = readFileSync(new URL('serve-static.mjs', root), 'utf8');

  assert.match(angular, /"configurations":\s*\{[\s\S]*"production"/);
  assert.match(angular, /"with":\s*"src\/environments\/environment\.prod\.ts"/);
  assert.match(packageJson, /"start:production":\s*"ng build --configuration production/);
  assert.match(server, /url\.pathname\.startsWith\('\/api\/app\/'\)/);
  assert.match(server, /http:\/\/gateway:8000/);
});
