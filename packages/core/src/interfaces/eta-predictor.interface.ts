export interface EtaInput {
  file_size_mb: number;
  page_count: number;
  output_format: 'epub' | 'mobi' | 'cbz';
  device: string;
  kcc_workers: number;
}

export interface IEtaPredictor {
  predict(input: EtaInput): number;
}
