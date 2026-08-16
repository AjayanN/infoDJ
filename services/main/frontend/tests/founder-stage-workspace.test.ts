import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import test from 'node:test';

const root = new URL('..', import.meta.url);

test('founder workspace focuses on comparable companies and Company 360', () => {
  const template = readFileSync(new URL('src/app.component.html', root), 'utf8');
  const source = readFileSync(new URL('src/main.ts', root), 'utf8');

  assert.match(template, /founder-stage-workspace/);
  assert.match(template, /See how companies moved through this stage/);
  assert.match(template, /founderPeerCompanies\(dash\)/);
  assert.match(template, /Open the Company 360 to explore its moves/);
  assert.doesNotMatch(template, /Evidence passport/);
  assert.match(source, /founderPeerCompanies\(dash: DashboardResponse\)/);
});