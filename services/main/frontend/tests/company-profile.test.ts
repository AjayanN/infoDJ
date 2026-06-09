import assert from 'node:assert/strict';
import test from 'node:test';

import {
  businessModelComponentLabel,
  businessModelRelationshipLabel,
  companyProfileItemLabel,
  companyProfileSectionHasData,
  companyProfileSectionLabel,
  dashboardRequestParams,
  kpiObservationFlags
} from '../src/app/company-profile.utils';

test('formats Company 360 section keys for display', () => {
  assert.equal(companyProfileSectionLabel('strategic_priorities'), 'Strategic Priorities');
});

test('labels KPI quality conditions without treating missing data as zero', () => {
  assert.deepEqual(kpiObservationFlags({
    is_estimated: true, is_restatement: false, is_non_comparable: true, definition_changed: false
  }), ['Estimated', 'Non-comparable']);
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

test('preserves company scope in dashboard requests and pagination', () => {
  assert.deepEqual(dashboardRequestParams('risk_signals', 2, 12, 'netflix'), {
    limit: '12', section: 'risk_signals', page: '2', company: 'netflix'
  });
  assert.deepEqual(dashboardRequestParams('', 1, 12, ''), { limit: '12' });
});

test('formats business-model components and relationships for accessible display', () => {
  assert.equal(businessModelComponentLabel('PAYER'), 'Who pays');
  assert.equal(businessModelComponentLabel('ASSET'), 'Key assets');
  assert.equal(businessModelComponentLabel('GEOGRAPHY'), 'Where it operates');
  assert.equal(businessModelRelationshipLabel('DELIVERED_THROUGH'), 'delivered through');
});
