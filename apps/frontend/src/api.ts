const BASE = '/api';

export async function prepareJob(filename: string, sizeBytes: number) {
  const r = await fetch(`${BASE}/jobs/prepare`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ filename, size_bytes: sizeBytes }),
  });
  if (!r.ok) throw new Error((await r.json()).error ?? 'prepare_failed');
  return r.json() as Promise<{ job_id: string; upload_url: string }>;
}

export async function uploadFile(jobId: string, file: File) {
  const form = new FormData();
  form.append('file', file);
  const r = await fetch(`${BASE}/jobs/${jobId}/upload`, { method: 'POST', body: form });
  if (!r.ok) throw new Error('upload_failed');
}

export async function finalizeJob(
  jobId: string,
  device: string,
  format: string,
  options: Record<string, boolean>,
) {
  const r = await fetch(`${BASE}/jobs/${jobId}/finalize`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ device, format, options }),
  });
  if (!r.ok) throw new Error((await r.json()).error ?? 'finalize_failed');
  return r.json() as Promise<{ job_id: string; eta_s: number; queue_position: number }>;
}

export function openProgressStream(jobId: string, onEvent: (data: unknown) => void): () => void {
  const es = new EventSource(`${BASE}/jobs/${jobId}/progress`);
  es.onmessage = (e) => { try { onEvent(JSON.parse(e.data)); } catch {} };
  return () => es.close();
}

export function downloadUrl(jobId: string) {
  return `${BASE}/jobs/${jobId}/download`;
}
