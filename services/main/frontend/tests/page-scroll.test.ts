import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import test from 'node:test';

const root = new URL('..', import.meta.url);

test('new in-app pages reset browser scroll to the start', () => {
  const source = readFileSync(new URL('src/main.ts', root), 'utf8');

  assert.match(source, /if \(changed\) \{\s*this\.scrollToPageStart\(\);\s*\}/);
  assert.match(source, /requestAnimationFrame\(\(\) => window\.scrollTo\(\{ top: 0, left: 0, behavior: 'auto' \}\)\)/);
});
