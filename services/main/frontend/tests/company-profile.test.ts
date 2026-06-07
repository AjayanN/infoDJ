import assert from 'node:assert/strict';
import test from 'node:test';

import {
  companyProfileItemLabel,
  companyProfileSectionHasData,
  companyProfileSectionLabel
} from '../src/app/company-profile.utils';

test('formats Company 360 section keys for display', () => {
  assert.equal(companyProfileSectionLabel('strategic_priorities'), 'Strategic Priorities');
});

test('formats structured Company 360 items without exposing object placeholders', () => {
  assert.equal(companyProfileItemLabel({ name: 'Greg Peters', role: 'CEO' }), 'Greg Peters');
  assert.equal(companyProfileItemLabel({ label: 'Subscriptions' }), 'Subscriptions');
});

test('detects available and unavailable Company 360 sections', () => {
  assert.equal(companyProfileSectionHasData({ text: '', items: [] }), false);
  assert.equal(companyProfileSectionHasData({ text: 'Subscription business', items: [] }), true);
  assert.equal(companyProfileSectionHasData({ text: '', items: ['Advertising'] }), true);
});
