export const DEVICES: Record<string, Record<string, string>> = {
  Kindle: {
    K1: 'Kindle 1', K2: 'Kindle 2', K3: 'Kindle 3', K34: 'Kindle Keyboard/Touch',
    K57: 'Kindle 5/7', KPW: 'Kindle Paperwhite 1/2', KV: 'Kindle Voyage',
    KPW34: 'Kindle Paperwhite 3/4/Oasis', K810: 'Kindle 8/10',
    KO: 'Kindle Oasis 2/3/Paperwhite 12', K11: 'Kindle 11',
    KPW5: 'Kindle Paperwhite 5/Signature Edition',
    KS1860: 'Kindle Scribe 1860', KS1920: 'Kindle Scribe 1920',
    KCS: 'Kindle Colorsoft',
  },
  Kobo: {
    KoMT: 'Kobo Mini/Touch', KoG: 'Kobo Glo', KoGHD: 'Kobo Glo HD',
    KoA: 'Kobo Aura', KoAHD: 'Kobo Aura HD', KoAH2O: 'Kobo Aura H2O',
    KoAO: 'Kobo Aura ONE', KoN: 'Kobo Nia',
    KoC: 'Kobo Clara HD/Clara 2E', KoCC: 'Kobo Clara Colour',
    KoL: 'Kobo Libra H2O/Libra 2', KoLC: 'Kobo Libra Colour',
    KoF: 'Kobo Forma', KoS: 'Kobo Sage', KoE: 'Kobo Elipsa',
  },
  reMarkable: {
    Rmk1: 'reMarkable 1', Rmk2: 'reMarkable 2', RmkP: 'reMarkable Paper Pro',
  },
  Other: { Other: 'Other (custom dimensions)' },
};

export const ALL_DEVICES: Record<string, string> = Object.assign({}, ...Object.values(DEVICES));

export const deviceLabel = (k: string): string => ALL_DEVICES[k] || k;

export function fmtBytes(b: number | null | undefined): string {
  if (!b) return '0 B';
  const u = ['B', 'KB', 'MB', 'GB'];
  const i = Math.floor(Math.log(b) / Math.log(1024));
  return parseFloat((b / 1024 ** i).toFixed(1)) + ' ' + u[i];
}

export function fmtTime(s: number | null | undefined): string {
  if (s == null || s <= 0) return '—';
  if (s < 60) return `${Math.round(s)}s`;
  return `${Math.floor(s / 60)}m ${Math.round(s % 60)}s`;
}

export function extIcon(n: string): 'archive' | 'fileText' | 'image' | 'book' {
  const e = (n.split('.').pop() || '').toLowerCase();
  if (['cbz', 'cbr', 'cb7', 'zip', 'rar', '7z'].includes(e)) return 'archive';
  if (e === 'pdf') return 'fileText';
  if (['jpg', 'jpeg', 'png', 'webp'].includes(e)) return 'image';
  if (['epub', 'mobi', 'kfx', 'azw3'].includes(e)) return 'book';
  return 'fileText';
}
