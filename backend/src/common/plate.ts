const INDIAN_STATE_CODES = new Set([
  'AN', 'AP', 'AR', 'AS', 'BR', 'CH', 'CG', 'DD', 'DL', 'DN', 'GA', 'GJ', 'HP', 'HR',
  'JH', 'JK', 'KA', 'KL', 'LA', 'LD', 'MH', 'ML', 'MN', 'MP', 'MZ', 'NL', 'OD', 'OR',
  'PB', 'PY', 'RJ', 'SK', 'TN', 'TR', 'TS', 'UK', 'UP', 'WB',
]);

const DIGIT_TO_LETTER: Record<string, string> = {
  '0': 'O', '1': 'I', '2': 'Z', '4': 'A', '5': 'S', '6': 'G', '7': 'T', '8': 'B',
};

const LETTER_TO_DIGIT: Record<string, string> = {
  'O': '0', 'Q': '0', 'D': '0', 'I': '1', 'L': '1', 'Z': '2',
  'A': '4', 'S': '5', 'G': '6', 'T': '7', 'B': '8',
};

const LAYOUTS: [number, number][] = [
  [2, 2], [2, 1], [2, 3], [1, 2], [1, 1], [1, 3],
];

export function cleanPlateText(raw: string): string {
  return raw.toUpperCase().replace(/[^A-Z0-9]/g, '');
}

interface Candidate {
  text: string;
  subs: number;
  stateOk: boolean;
}

function fitWindow(window: string, d: number, s: number): Candidate | null {
  const kinds = 'LL' + 'D'.repeat(d) + 'L'.repeat(s) + 'DDDD';
  if (window.length !== kinds.length) return null;
  if (d === 1 && window[2] === '0') return null;

  const out: string[] = [];
  let subs = 0;
  const seriesStart = 2 + d;
  const seriesEnd = seriesStart + s;

  for (let i = 0; i < window.length; i++) {
    const ch = window[i]!;
    const kind = kinds[i]!;

    if (kind === 'L') {
      if (/[A-Z]/.test(ch)) {
        if (i >= seriesStart && i < seriesEnd && (ch === 'I' || ch === 'O' || ch === 'Q')) {
          return null;
        }
        out.push(ch);
      } else if (ch in DIGIT_TO_LETTER) {
        const sub = DIGIT_TO_LETTER[ch]!;
        if (i >= seriesStart && i < seriesEnd && (sub === 'I' || sub === 'O' || sub === 'Q')) {
          return null;
        }
        out.push(sub);
        subs++;
      } else {
        return null;
      }
    } else {
      if (/[0-9]/.test(ch)) {
        out.push(ch);
      } else if (ch in LETTER_TO_DIGIT) {
        out.push(LETTER_TO_DIGIT[ch]!);
        subs++;
      } else {
        return null;
      }
    }
  }

  const text = out.join('');
  return {
    text,
    subs,
    stateOk: INDIAN_STATE_CODES.has(text.substring(0, 2)),
  };
}

export function correctIndianPlate(t: string): Candidate | null {
  if (t.length > 16) return null;
  let best: Candidate | null = null;
  let bestKey: [number, number, number, number] | null = null;

  for (let start = 0; start < t.length; start++) {
    for (let end = start + 8; end <= Math.min(t.length, start + 11); end++) {
      for (let pref = 0; pref < LAYOUTS.length; pref++) {
        const [d, s] = LAYOUTS[pref]!;
        const cand = fitWindow(t.substring(start, end), d, s);
        if (!cand) continue;

        const endDiscarded = t.length - end;
        const discarded = start + endDiscarded;
        if (!cand.stateOk && discarded > 1) continue;

        const cost = cand.subs + endDiscarded * 2 + start;
        const key: [number, number, number, number] = [cand.stateOk ? 0 : 1, cost, cand.subs, pref];

        if (
          !bestKey ||
          key[0] < bestKey[0] ||
          (key[0] === bestKey[0] && key[1] < bestKey[1]) ||
          (key[0] === bestKey[0] && key[1] === bestKey[1] && key[2] < bestKey[2]) ||
          (key[0] === bestKey[0] && key[1] === bestKey[1] && key[2] === bestKey[2] && key[3] < bestKey[3])
        ) {
          best = cand;
          bestKey = key;
        }
      }
    }
  }

  return best;
}

export function normalisePlate(raw: string): string {
  const cleaned = cleanPlateText(raw);
  const indian = correctIndianPlate(cleaned);
  if (indian) {
    return indian.text;
  }
  return cleaned;
}
