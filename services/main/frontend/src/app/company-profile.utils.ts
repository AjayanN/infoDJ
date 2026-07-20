export function companyProfileSectionLabel(key: string): string {
  return key.replace(/_/g, ' ').replace(/\b\w/g, (letter) => letter.toUpperCase());
}

export function companyProfileItemLabel(item: unknown): string {
  if (typeof item === 'string') {
    return item;
  }
  if (item && typeof item === 'object') {
    const row = item as Record<string, unknown>;
    return String(row['name'] || row['label'] || row['title'] || row['value'] || JSON.stringify(row));
  }
  return String(item || '');
}

export function companyProfileSectionHasData(section: { text: string; items: unknown[] }): boolean {
  return Boolean(section.text.trim()) || section.items.length > 0;
}

export function dashboardRequestParams(section = '', page = 1, limit = 12, company = ''): Record<string, string> {
  const params: Record<string, string> = { limit: String(limit) };
  if (section) {
    params['section'] = section;
    params['page'] = String(page);
  }
  if (company) {
    params['company'] = company;
  }
  return params;
}

export function businessModelComponentLabel(type: string): string {
  const labels: Record<string, string> = {
    PAYER: 'Who pays',
    USER: 'Who uses',
    OFFERING: 'What they receive',
    REVENUE: 'How revenue is earned',
    CHANNEL: 'How it is delivered',
    GEOGRAPHY: 'Where it operates',
    PARTNER: 'Key partners',
    COST: 'Major costs',
    ASSET: 'Key assets'
  };
  return labels[type] || type;
}

export function businessModelRelationshipLabel(type: string): string {
  return type.toLowerCase().replace(/_/g, ' ');
}

export function managementPromiseLabel(value: string): string {
  return value.toLowerCase().replace(/_/g, ' ').replace(/(^|\s)\S/g, (letter) => letter.toUpperCase());
}

export function kpiObservationFlags(observation: {
  is_estimated: boolean; is_restatement: boolean; is_non_comparable: boolean; definition_changed: boolean;
}): string[] {
  const flags: string[] = [];
  if (observation.is_estimated) flags.push('Estimated');
  if (observation.is_restatement) flags.push('Restated');
  if (observation.is_non_comparable) flags.push('Non-comparable');
  if (observation.definition_changed) flags.push('Definition changed');
  return flags;
}

export type SourceLensRecord = {
  id: number;
  source_api: string;
  title: string;
  publisher: string;
  url: string;
  published_date: string | null;
  snippet: string;
  status: string;
  updated_at: string;
  evidence_context?: string[];
  evidence_context_label?: string;
  snapshot_dates?: string[];
};

export function deduplicateSourceLensRecords(sources: SourceLensRecord[]): SourceLensRecord[] {
  const unique = new Map<string, SourceLensRecord>();
  for (const source of sources) {
    const key = source.url.trim().toLowerCase() || `${source.source_api}:${source.title}`.toLowerCase();
    if (!unique.has(key)) unique.set(key, source);
  }
  return Array.from(unique.values());
}

export function sourceLensWhyUsed(source: SourceLensRecord): string {
  if (source.evidence_context_label) return source.evidence_context_label;
  if (source.evidence_context?.length) return source.evidence_context.join(', ');
  return 'Used in this Company 360 view.';
}
