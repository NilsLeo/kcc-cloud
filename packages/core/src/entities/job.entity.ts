export type JobStatus =
  | 'UPLOADING' | 'QUEUED' | 'PROCESSING' | 'COMPLETE'
  | 'DOWNLOADED' | 'ERRORED' | 'CANCELLED' | 'ABANDONED';

export interface Job {
  id: string;
  status: JobStatus;
  filename: string;
  output_filename: string | null;
  format: 'epub' | 'mobi' | 'cbz' | null;
  device: string | null;
  page_count: number | null;
  file_size_bytes: number | null;
  output_size_bytes: number | null;
  eta_s: number | null;
  elapsed_s: number | null;
  error_message: string | null;
  input_path: string | null;
  output_path: string | null;
  download_url: string | null;
  created_at: Date;
  queued_at: Date | null;
  processing_at: Date | null;
  completed_at: Date | null;
}
