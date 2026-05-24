export type AdvancedItem =
  | { type: 'toggle'; k: string; t: string; s?: string }
  | { type: 'select'; k: string; t: string; options: Array<[string | number, string]> }
  | { type: 'slider'; k: string; t: string; min: number; max: number; step: number }
  | { type: 'number'; k: string; t: string; suffix?: string; requiredForOther?: boolean }
  | { type: 'text'; k: string; t: string };

export type AdvancedSection = {
  title: string;
  icon: string;
  items: AdvancedItem[];
  note?: string;
};

export const ADVANCED_SECTIONS: AdvancedSection[] = [
  { title: 'Image processing', icon: 'image', items: [
    { type: 'toggle', k: 'upscale',        t: 'Upscale images',    s: 'Resize images smaller than device resolution' },
    { type: 'toggle', k: 'stretch',        t: 'Stretch to fill',   s: "No borders — fill the entire screen" },
    { type: 'toggle', k: 'hq',             t: 'High quality',      s: 'Slower processing, better magnification' },
    { type: 'toggle', k: 'autoLevel',      t: 'Auto-level',        s: 'Automatic contrast adjustment' },
    { type: 'toggle', k: 'forceColor',     t: 'Force color',       s: "Don't convert to grayscale" },
    { type: 'toggle', k: 'forceGrayscale', t: 'Force grayscale',   s: 'Convert everything to grayscale' },
  ]},
  { title: 'Cropping & margins', icon: 'crop', items: [
    { type: 'select', k: 'marginDetection', t: 'Margin detection',
      options: [[0, 'None'], [1, 'Light'], [2, 'Medium'], [3, 'Aggressive']] },
    { type: 'toggle', k: 'removePageNumbers', t: 'Remove page numbers', s: 'Strip page-number text from margins' },
    { type: 'toggle', k: 'preserveMargins',   t: 'Preserve margins',    s: 'Keep original page margins' },
    { type: 'slider', k: 'croppingPower',     t: 'Cropping power',      min: 0, max: 2, step: 0.1 },
  ]},
  { title: 'Borders', icon: 'square', items: [
    { type: 'toggle', k: 'blackBorderDetection', t: 'Black border detection', s: 'Auto-detect black borders' },
    { type: 'toggle', k: 'whiteBorderDetection', t: 'White border detection', s: 'Auto-detect white borders' },
    { type: 'toggle', k: 'forceBlackBorders',    t: 'Force black borders',    s: 'Override with black borders' },
    { type: 'toggle', k: 'forceWhiteBorders',    t: 'Force white borders',    s: 'Override with white borders' },
  ]},
  { title: 'Manga-specific', icon: 'bookOpen', items: [
    { type: 'toggle', k: 'mangaStyle',  t: 'Manga style',     s: 'Right-to-left reading + page split (set by mode toggle)' },
    { type: 'toggle', k: 'twoPanel',    t: 'Two-panel split', s: 'Show two panels in Panel View, not four' },
    { type: 'toggle', k: 'webtoon',     t: 'Webtoon mode',    s: 'Vertical-scroll webtoon processing' },
    { type: 'toggle', k: 'spreadShift', t: 'Spread shift',    s: 'Shift two-page spreads to align' },
  ]},
  { title: 'Output quality', icon: 'fileText', items: [
    { type: 'select', k: 'outputFormat', t: 'Output format',
      options: [['Auto', 'Auto'], ['MOBI', 'MOBI'], ['EPUB', 'EPUB'], ['CBZ', 'CBZ'], ['KFX', 'KFX'], ['MOBI+EPUB', 'MOBI+EPUB']] },
    { type: 'number', k: 'targetSize',   t: 'Target file size', suffix: 'MB' },
    { type: 'slider', k: 'gamma',        t: 'Gamma',            min: 0, max: 2, step: 0.1 },
    { type: 'toggle', k: 'mozjpeg',      t: 'mozJPEG',          s: 'Use mozJPEG compression (smaller files)' },
    { type: 'toggle', k: 'forcePng',     t: 'Force PNG',        s: 'Skip JPEG, output PNGs' },
    { type: 'text',   k: 'author',       t: 'Author tag' },
    { type: 'toggle', k: 'noKepub',      t: 'No .kepub',        s: 'Use .epub instead of .kepub.epub' },
  ]},
  { title: 'Orientation', icon: 'chevronsRight', items: [
    { type: 'select', k: 'rotation', t: 'Rotation',
      options: [[0, '0°'], [90, '90°'], [180, '180°'], [270, '270°']] },
    { type: 'toggle', k: 'autoRotation',   t: 'Auto-rotation',   s: 'Rotate landscape pages automatically' },
    { type: 'toggle', k: 'landscapeSplit', t: 'Landscape split', s: 'Split landscape pages into two' },
  ]},
  { title: 'Processing', icon: 'settings', items: [
    { type: 'toggle', k: 'noProcessing', t: 'No processing', s: "Don't modify images at all" },
    { type: 'select', k: 'splitter',     t: 'Splitter mode',
      options: [[0, 'Split'], [1, 'Rotate'], [2, 'Both']] },
  ]},
  { title: 'Custom profile', icon: 'smartphone', items: [
    { type: 'number', k: 'customWidth',  t: 'Custom width',  suffix: 'px', requiredForOther: true },
    { type: 'number', k: 'customHeight', t: 'Custom height', suffix: 'px', requiredForOther: true },
  ], note: 'Required when "Other" device profile is selected.' },
];

export type AdvancedOptions = {
  customWidth: number; customHeight: number;
  hq: boolean; twoPanel: boolean; webtoon: boolean; spreadShift: boolean; mangaStyle: boolean;
  upscale: boolean; stretch: boolean; noProcessing: boolean; splitter: number;
  gamma: number; targetSize: number; outputFormat: string; author: string;
  noKepub: boolean; forceColor: boolean; forceGrayscale: boolean; autoLevel: boolean;
  marginDetection: number; removePageNumbers: boolean; preserveMargins: boolean; croppingPower: number;
  blackBorderDetection: boolean; whiteBorderDetection: boolean; forceBlackBorders: boolean; forceWhiteBorders: boolean;
  mozjpeg: boolean; forcePng: boolean;
  rotation: number; autoRotation: boolean; landscapeSplit: boolean;
};

export const ADVANCED_DEFAULTS: AdvancedOptions = {
  customWidth: 0, customHeight: 0,
  hq: false, twoPanel: false, webtoon: false, spreadShift: false, mangaStyle: false,
  upscale: false, stretch: false, noProcessing: false, splitter: 0,
  gamma: 0, targetSize: 400, outputFormat: 'Auto', author: 'KCC',
  noKepub: false, forceColor: false, forceGrayscale: false, autoLevel: false,
  marginDetection: 0, removePageNumbers: false, preserveMargins: false, croppingPower: 1,
  blackBorderDetection: false, whiteBorderDetection: false, forceBlackBorders: false, forceWhiteBorders: false,
  mozjpeg: true, forcePng: false,
  rotation: 0, autoRotation: false, landscapeSplit: false,
};
