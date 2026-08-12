import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import test from 'node:test';

const root = new URL('..', import.meta.url);

test('Company 360 labels revenue-source counts and omits development footer text', () => {
  const template = readFileSync(new URL('src/app.component.html', root), 'utf8');

  assert.match(template, /Revenue streams/);
  assert.match(template, /revenueSourceCount\(companyView\)/);
  assert.match(template, /Open revenue map/);
  assert.doesNotMatch(template, /InfoDJ Sprint 1/);
  assert.doesNotMatch(template, /Razorpay and Google secrets stay server-side/);
});
