/**
 * Escapes a cell value for CSV output with formula injection (CSV injection) protection.
 *
 * If a cell string starts with =, +, -, @, \t, or \r, a single quote (') is prepended.
 * Any cell containing quotes, commas, or newlines is wrapped in double quotes,
 * with inner double quotes escaped as "".
 */
export function csvCell(val: unknown): string {
  if (val === null || val === undefined) {
    return '';
  }

  let str = String(val);

  // Formula injection defense (ADR 0024)
  if (/^[=+\-@\t\r]/.test(str)) {
    str = "'" + str;
  }

  if (/[",\n\r]/.test(str)) {
    return `"${str.replace(/"/g, '""')}"`;
  }

  return str;
}
