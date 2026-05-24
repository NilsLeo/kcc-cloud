import { IEtaPredictor, EtaInput } from '@mgc/core';

export class FormulaEtaPredictor implements IEtaPredictor {
  predict(input: EtaInput): number {
    // Calibrated from empirical data (see tools/eta_predict.py reference)
    const { file_size_mb, page_count, output_format, kcc_workers } = input;
    const mbPerPage = page_count > 0 ? file_size_mb / page_count : file_size_mb;
    const basePerPage = output_format === 'mobi' ? 3.5 : 2.0;
    const workerSpeedup = Math.max(1, Math.log2(kcc_workers + 1));
    return Math.max(10, Math.round((page_count * basePerPage * mbPerPage) / workerSpeedup));
  }
}
