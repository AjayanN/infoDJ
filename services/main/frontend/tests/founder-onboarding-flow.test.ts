import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import test from 'node:test';

const root = new URL('..', import.meta.url);

test('founder onboarding resumes at the first unanswered question and opens a focus plan', () => {
  const source = readFileSync(new URL('src/main.ts', root), 'utf8');
  const template = readFileSync(new URL('src/app.component.html', root), 'utf8');

  assert.match(source, /private syncFounderSetupStep\(\): void/);
  assert.match(source, /firstMissingStep = answers\.findIndex/);
  assert.match(source, /this\.setPage\('focus-plan'\)/);
  assert.match(source, /this\.setPage\('focus-plan', false\)/);
  assert.match(template, /\*ngSwitchCase="'focus-plan'"/);
  assert.match(template, /What did similar companies do\?/);
  assert.match(template, /Original source/);
});
