import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import test from 'node:test';

const root = new URL('..', import.meta.url);

test('public login explains the InfoDJ product before authentication', () => {
  const template = readFileSync(new URL('src/app.component.html', root), 'utf8');
  const styles = readFileSync(new URL('src/styles.css', root), 'utf8');

  assert.match(template, /Evidence before ego\.<\/strong> Progress before noise\./);
  assert.match(template, /Why InfoDJ exists/);
  assert.match(template, /Common questions/);
  assert.match(template, /Company 360 is there when you want the underlying detail/);
  assert.match(styles, /@keyframes entry-rise/);
  assert.match(styles, /prefers-reduced-motion: reduce/);
});