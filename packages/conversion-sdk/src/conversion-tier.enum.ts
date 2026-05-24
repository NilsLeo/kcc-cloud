export enum ConversionTier {
  SMALL = 'small',
  MEDIUM = 'medium',
  LARGE = 'large',
}

export function getTierForSize(sizeBytes: number): ConversionTier {
  const mb = sizeBytes / (1024 * 1024);
  if (mb < 100) return ConversionTier.SMALL;
  if (mb < 500) return ConversionTier.MEDIUM;
  return ConversionTier.LARGE;
}
