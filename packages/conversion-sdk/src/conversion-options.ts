export interface ConversionOptions {
  device: string;
  format: 'epub' | 'mobi' | 'cbz';
  manga: boolean;
  hq: boolean;
  webtoon: boolean;
  two_panel: boolean;
  upscale: boolean;
}
