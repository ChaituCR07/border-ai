export function formatPlateDisplay(raw?: string | null): string {
  if (!raw) return '–';
  const clean = raw.trim().toUpperCase();
  // Standard Indian 10-char plate format: KA01AB1234 -> KA 01 AB 1234
  const indMatch = /^([A-Z]{2})(\d{1,2})([A-Z]{1,3})(\d{4})$/.exec(clean);
  if (indMatch && indMatch[1] && indMatch[2] && indMatch[3] && indMatch[4]) {
    return `${indMatch[1]} ${indMatch[2]} ${indMatch[3]} ${indMatch[4]}`;
  }
  return clean;
}

export const formatPlate = formatPlateDisplay;
