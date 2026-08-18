import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import test from 'node:test';

const root = new URL('..', import.meta.url);

test('public login tells a founder boardroom-to-plan story before authentication', () => {
  const template = readFileSync(new URL('src/app.component.html', root), 'utf8');
  const styles = readFileSync(new URL('src/styles.css', root), 'utf8');
  const component = readFileSync(new URL('src/main.ts', root), 'utf8');

  assert.match(template, /01 — The hard meeting/);
  assert.match(template, /Discover InfoDJ/);
  assert.match(template, /See what comparable companies did/);
  assert.match(template, /Bring one clear next step to the next meeting/);
  assert.match(template, /Build my focus plan/);
  assert.match(styles, /\.boardroom-problem-scene/);
  assert.match(styles, /scroll-snap-type: y mandatory/);
  assert.match(styles, /scroll-snap-stop: always/);
  assert.match(styles, /\.scroll-scene\.is-active/);
  assert.match(styles, /@keyframes comparable-card-arrive/);
  assert.match(styles, /@media \(pointer: coarse\)/);
  assert.match(component, /IntersectionObserver/);
  assert.doesNotMatch(styles, /\.founder-entry \.auth-card::before/);
  assert.match(styles, /prefers-reduced-motion: reduce/);
});
