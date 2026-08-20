import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import test from 'node:test';

const root = new URL('..', import.meta.url);

test('public login uses continuous cinematic scrolling through the existing founder visuals', () => {
  const template = readFileSync(new URL('src/app.component.html', root), 'utf8');
  const styles = readFileSync(new URL('src/styles.css', root), 'utf8');
  const component = readFileSync(new URL('src/main.ts', root), 'utf8');

  assert.match(template, /01 — The boardroom question/);
  assert.match(template, /02 — Define the proof point/);
  assert.match(template, /See what comparable companies did/);
  assert.match(template, /Bring one clear next step to the next meeting/);
  assert.match(template, /Build my focus plan/);
  assert.match(template, /boardroom-visual/);
  assert.match(template, /infodj-screen/);
  assert.match(template, /comparable-card/);
  assert.match(template, /meeting-task-card/);
  assert.match(styles, /\.boardroom-problem-scene/);
  assert.match(styles, /\.boardroom-problem-scene\.story-page-leaving \.issue-note/);
  assert.match(styles, /\.discovery-scene\.story-page-entering \.infodj-screen/);
  assert.match(styles, /\.evidence-story-scene\.story-page-entering \.comparable-card/);
  assert.match(styles, /\.meeting-outcome-scene\.story-page-entering \.meeting-task-card/);
  assert.match(styles, /@keyframes question-note-to-screen/);
  assert.doesNotMatch(template, /story-journey-map/);
  assert.doesNotMatch(styles, /\.legacy-story-visual/);
  assert.match(styles, /scroll-snap-type: none/);
  assert.match(styles, /animation-timeline: view\(\)/);
  assert.match(styles, /@supports \(animation-timeline: view\(\)\)/);
  assert.match(styles, /@keyframes cinematic-founder-zoom/);
  assert.match(styles, /\.scroll-scene\.is-active/);
  assert.match(styles, /@keyframes comparable-card-arrive/);
  assert.doesNotMatch(styles, /@keyframes story-camera-arrive/);
  assert.doesNotMatch(styles, /@keyframes story-camera-away/);
  assert.match(styles, /@media \(pointer: coarse\) and \(min-width: 700px\)/);
  assert.match(component, /IntersectionObserver/);
  assert.doesNotMatch(component, /storyRoot\.addEventListener\('wheel'/);
  assert.doesNotMatch(styles, /\.founder-entry \.auth-card::before/);
  assert.match(styles, /prefers-reduced-motion: reduce/);
});
