import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import test from 'node:test';

const root = new URL('..', import.meta.url);

test('public login transforms one founder decision map from boardroom question to action plan', () => {
  const template = readFileSync(new URL('src/app.component.html', root), 'utf8');
  const styles = readFileSync(new URL('src/styles.css', root), 'utf8');
  const component = readFileSync(new URL('src/main.ts', root), 'utf8');

  assert.match(template, /01 — The boardroom question/);
  assert.match(template, /02 — Define the proof point/);
  assert.match(template, /See what comparable companies did/);
  assert.match(template, /Bring one clear next step to the next meeting/);
  assert.match(template, /Build my focus plan/);
  assert.match(template, /story-journey-map/);
  assert.match(template, /What should you prove next\?/);
  assert.match(template, /COMPARABLE MOVE/);
  assert.match(template, /NEXT MEETING/);
  assert.match(styles, /\.boardroom-problem-scene/);
  assert.match(styles, /\.story-journey-map/);
  assert.match(styles, /data-story-stage="1"/);
  assert.match(styles, /data-story-stage="2"/);
  assert.match(styles, /data-story-stage="3"/);
  assert.match(styles, /data-story-stage="4"/);
  assert.match(styles, /\.journey-link/);
  assert.match(styles, /scroll-snap-type: y mandatory/);
  assert.match(styles, /scroll-snap-stop: always/);
  assert.match(styles, /\.scroll-scene\.is-active/);
  assert.match(styles, /@keyframes comparable-card-arrive/);
  assert.doesNotMatch(styles, /@keyframes story-camera-arrive/);
  assert.doesNotMatch(styles, /@keyframes story-camera-away/);
  assert.match(styles, /@media \(pointer: coarse\) and \(min-width: 700px\)/);
  assert.match(component, /IntersectionObserver/);
  assert.match(component, /moveStoryPage/);
  assert.doesNotMatch(styles, /\.founder-entry \.auth-card::before/);
  assert.match(styles, /prefers-reduced-motion: reduce/);
});
