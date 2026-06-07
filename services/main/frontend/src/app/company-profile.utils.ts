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
