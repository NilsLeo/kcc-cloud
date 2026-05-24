import { ConversionOptions } from '@mgc/conversion-sdk';

export interface ConversionJobPayload {
  job_id: string;
  input_path: string;
  output_dir: string;
  kcc_workers: number;
  options: ConversionOptions;
}
