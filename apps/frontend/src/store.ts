import { defineStore } from 'pinia';
import { ref, reactive } from 'vue';
import * as api from './api';
import { ADVANCED_DEFAULTS, type AdvancedOptions } from './lib/advancedDefaults';
import { deviceLabel } from './lib/formatters';

export type QueueStatus = 'UPLOADING' | 'QUEUED' | 'PROCESSING' | 'COMPLETE' | 'ERRORED';

export type QueueItem = {
  id: string;
  file: File | null;
  name: string;
  size: number;
  status: QueueStatus;
  progress: number;
  confirmedProgress: number;
  deviceProfile: string;
  outputFormat: string;
  jobId: string | null;
  error: string | null;
  eta: number | null;
  statusDetail: string | null;
  outputSize: number | null;
  duration: number | null;
  convertedName: string | null;
};

export type CompletedJob = {
  jobId: string;
  inputName: string;
  outputName: string;
  completedAt: string;
  deviceLabel: string;
  format: string;
  outputSize?: number | null;
};

const STORAGE_KEY = 'mgc_downloads';

function loadDownloads(): CompletedJob[] {
  try {
    return JSON.parse(localStorage.getItem(STORAGE_KEY) ?? '[]');
  } catch {
    return [];
  }
}

function saveDownloads(list: CompletedJob[]) {
  localStorage.setItem(STORAGE_KEY, JSON.stringify(list.slice(0, 50)));
}

function genId() {
  return Math.random().toString(36).slice(2);
}

function inferFormat(profile: string, requested: string): string {
  if (requested && requested !== 'Auto') return requested;
  if (profile.startsWith('Ko')) return 'EPUB';
  return 'MOBI';
}

export const useStore = defineStore('main', () => {
  const items = ref<QueueItem[]>([]);
  const downloads = ref<CompletedJob[]>(loadDownloads());
  const selectedProfile = ref<string>('KPW5');
  const advancedOptions = reactive<AdvancedOptions>({ ...ADVANCED_DEFAULTS });

  const sseClosers = new Map<string, () => void>();

  function pushDownload(job: CompletedJob) {
    downloads.value = [job, ...downloads.value];
    saveDownloads(downloads.value);
  }

  function removeDownload(jobId: string) {
    downloads.value = downloads.value.filter((d) => d.jobId !== jobId);
    saveDownloads(downloads.value);
  }

  function cancelItem(id: string) {
    const item = items.value.find((i) => i.id === id);
    if (item?.jobId) {
      const closer = sseClosers.get(item.jobId);
      closer?.();
      sseClosers.delete(item.jobId);
    }
    items.value = items.value.filter((i) => i.id !== id);
  }

  async function addFiles(files: File[]) {
    for (const file of files) {
      const item: QueueItem = reactive({
        id: genId(),
        file,
        name: file.name,
        size: file.size,
        status: 'UPLOADING',
        progress: 0,
        confirmedProgress: 0,
        deviceProfile: selectedProfile.value,
        outputFormat: inferFormat(selectedProfile.value, advancedOptions.outputFormat),
        jobId: null,
        error: null,
        eta: null,
        statusDetail: null,
        outputSize: null,
        duration: null,
        convertedName: null,
      });
      items.value.push(item);
      // Kick off upload independently (don't await — let them run in parallel)
      void uploadAndStart(item);
    }
  }

  async function uploadAndStart(item: QueueItem) {
    try {
      // 1. Prepare
      const { job_id } = await api.prepareJob(item.name, item.size);
      item.jobId = job_id;

      // 2. Fake progress ramp (0 → 90% over ~1.5s)
      let progressTimer: number | null = null;
      const startTs = Date.now();
      progressTimer = window.setInterval(() => {
        const elapsed = (Date.now() - startTs) / 1500;
        const p = Math.min(90, elapsed * 90);
        item.progress = p;
        item.confirmedProgress = Math.max(0, p - 10);
      }, 80);

      // 3. Upload
      if (item.file) {
        await api.uploadFile(job_id, item.file);
      }

      if (progressTimer != null) clearInterval(progressTimer);
      item.progress = 100;
      item.confirmedProgress = 100;
      item.status = 'QUEUED';
      item.statusDetail = 'Waiting for a worker…';

      // 4. Finalize
      const apiOptions: Record<string, boolean> = {
        manga: !!advancedOptions.mangaStyle,
        hq: !!advancedOptions.hq,
        webtoon: !!advancedOptions.webtoon,
        two_panel: !!advancedOptions.twoPanel,
        upscale: !!advancedOptions.upscale,
      };
      await api.finalizeJob(job_id, item.deviceProfile, item.outputFormat, apiOptions);

      // 5. SSE
      const startTime = Date.now();
      const close = api.openProgressStream(job_id, (raw) => {
        const data = raw as any;
        if (typeof data.progress === 'number') {
          item.progress = data.progress;
          if (item.status === 'QUEUED') item.status = 'PROCESSING';
        }
        if (data.message) item.statusDetail = data.message;
        if (typeof data.eta_s === 'number') item.eta = data.eta_s;
        if (data.phase && data.phase !== 'queued' && item.status === 'QUEUED') {
          item.status = 'PROCESSING';
        }
        if (data.status === 'COMPLETE') {
          item.status = 'COMPLETE';
          item.progress = 100;
          item.convertedName = data.output_filename ?? item.name.replace(/\.[^.]+$/, '') + '.' + item.outputFormat.toLowerCase();
          item.outputSize = data.output_size ?? null;
          item.duration = Math.round((Date.now() - startTime) / 1000);
          pushDownload({
            jobId: job_id,
            inputName: item.name,
            outputName: item.convertedName ?? item.name,
            completedAt: new Date().toISOString(),
            deviceLabel: item.deviceProfile,
            format: item.outputFormat,
            outputSize: item.outputSize,
          });
          const closer = sseClosers.get(job_id);
          closer?.();
          sseClosers.delete(job_id);
        }
        if (data.status === 'ERRORED') {
          item.status = 'ERRORED';
          item.error = data.message ?? 'Conversion failed';
          const closer = sseClosers.get(job_id);
          closer?.();
          sseClosers.delete(job_id);
        }
      });
      sseClosers.set(job_id, close);
    } catch (e: any) {
      item.status = 'ERRORED';
      item.error = e?.message ?? 'Unknown error';
    }
  }

  function retryItem(id: string) {
    const item = items.value.find((i) => i.id === id);
    if (!item) return;
    item.status = 'UPLOADING';
    item.progress = 0;
    item.confirmedProgress = 0;
    item.error = null;
    item.jobId = null;
    item.outputSize = null;
    item.duration = null;
    item.convertedName = null;
    void uploadAndStart(item);
  }

  return {
    items,
    downloads,
    selectedProfile,
    advancedOptions,
    addFiles,
    cancelItem,
    removeDownload,
    retryItem,
    pushDownload,
  };
});

export { deviceLabel };
