import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import test from 'node:test';

const root = new URL('..', import.meta.url);

test('public login presents a progressive market-to-plan story before authentication', () => {
  const template = readFileSync(new URL('src/app.component.html', root), 'utf8');
  const styles = readFileSync(new URL('src/styles.css', root), 'utf8');

  assert.match(template, /01 — Notice the signal/);
  assert.match(template, /02 — Understand why/);
  assert.match(template, /03 — Make it useful/);
  assert.match(template, /Build my focused plan/);
  assert.match(styles, /\.scroll-scene/);
  assert.match(styles, /@keyframes market-draw/);
  assert.match(styles, /prefers-reduced-motion: reduce/);
});
