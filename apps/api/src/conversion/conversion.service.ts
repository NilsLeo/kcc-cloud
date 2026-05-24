import {
  Injectable, NotFoundException, ConflictException,
  BadRequestException, PayloadTooLargeException, UnsupportedMediaTypeException,
  Logger, OnModuleInit,
} from '@nestjs/common';
import { InjectQueue } from '@nestjs/bullmq';
import { Queue } from 'bullmq';
import { Response } from 'express';
import * as fs from 'fs';
import * as fsPromises from 'fs/promises';
import * as path from 'path';
import { v4 as uuidv4 } from 'uuid';
import { PDFDocument } from 'pdf-lib';

import { QUEUE_NAMES, ConversionJobPayload } from '@mgc/queue';
import { getTierForSize, ConversionTier, JobStatus } from '@mgc/conversion-sdk';
import { BaseJobRepository } from '@mgc/db';
import { RedisService } from '../redis/redis.service';
import { FormulaEtaPredictor } from './eta-predictor';

const MAX_SIZE = 2 * 1024 * 1024 * 1024; // 2 GB
const ACCEPTED_EXTENSIONS = new Set(['.pdf', '.cbz', '.cbr', '.cb7', '.zip', '.rar', '.epub']);
const STORAGE_PATH = process.env.STORAGE_PATH ?? '/data/files';
const KCC_WORKERS_MAP: Record<ConversionTier, number> = {
  [ConversionTier.SMALL]: 1,
  [ConversionTier.MEDIUM]: 2,
  [ConversionTier.LARGE]: 2,
};

@Injectable()
export class ConversionService implements OnModuleInit {
  private readonly logger = new Logger(ConversionService.name);
  private readonly eta = new FormulaEtaPredictor();
  private repo!: BaseJobRepository;

  constructor(
    @InjectQueue(QUEUE_NAMES.SMALL)  private readonly smallQueue: Queue,
    @InjectQueue(QUEUE_NAMES.MEDIUM) private readonly mediumQueue: Queue,
    @InjectQueue(QUEUE_NAMES.LARGE)  private readonly largeQueue: Queue,
    private readonly redis: RedisService,
  ) {}

  onModuleInit() {
    this.repo = new BaseJobRepository(process.env.DATABASE_URL ?? 'file:/data/mgc.db');
  }

  async prepare(filename: string, sizeBytes: number): Promise<{ job_id: string; upload_url: string }> {
    if (sizeBytes > MAX_SIZE) throw new PayloadTooLargeException('file_too_large');

    const ext = path.extname(filename).toLowerCase();
    if (!ACCEPTED_EXTENSIONS.has(ext)) throw new UnsupportedMediaTypeException('unsupported_type');

    const jobId = uuidv4();
    const inputDir = path.join(STORAGE_PATH, 'input', jobId);
    await fsPromises.mkdir(inputDir, { recursive: true });

    await this.redis.setJobHash(jobId, {
      status: JobStatus.UPLOADING,
      filename,
      file_size_bytes: sizeBytes,
      created_at: new Date().toISOString(),
    });

    return { job_id: jobId, upload_url: `/api/jobs/${jobId}/upload` };
  }

  async upload(jobId: string, file: Express.Multer.File): Promise<void> {
    const hash = await this.redis.getJobHash(jobId);
    if (!hash || !hash['status']) throw new NotFoundException();

    const inputDir = path.join(STORAGE_PATH, 'input', jobId);
    const ext = path.extname(hash['filename'] ?? '').toLowerCase() || '.pdf';
    const dest = path.join(inputDir, `input${ext}`);
    await fsPromises.writeFile(dest, file.buffer);

    await this.redis.setJobHash(jobId, { input_path: dest });
  }

  async finalize(
    jobId: string,
    device: string,
    format: string,
    options: { manga?: boolean; hq?: boolean; webtoon?: boolean; two_panel?: boolean; upscale?: boolean },
  ): Promise<{ job_id: string; eta_s: number; queue_position: number }> {
    const hash = await this.redis.getJobHash(jobId);
    if (!hash || !hash['status']) throw new NotFoundException();
    if (hash['status'] !== JobStatus.UPLOADING) throw new ConflictException('already_finalized');
    if (!hash['input_path']) throw new BadRequestException('upload_required');

    const fmt = (format || 'epub').toLowerCase() as 'epub' | 'mobi' | 'cbz';
    const sizeBytes = parseInt(hash['file_size_bytes'] ?? '0', 10);
    const tier = getTierForSize(sizeBytes);
    const kccWorkers = KCC_WORKERS_MAP[tier];

    let pageCount = 0;
    if (hash['input_path'].endsWith('.pdf')) {
      try {
        const buf = await fsPromises.readFile(hash['input_path']);
        const doc = await PDFDocument.load(buf, { ignoreEncryption: true });
        pageCount = doc.getPageCount();
      } catch { /* non-fatal */ }
    }

    const etaS = this.eta.predict({
      file_size_mb: sizeBytes / (1024 * 1024),
      page_count: pageCount || 50,
      output_format: fmt,
      device,
      kcc_workers: kccWorkers,
    });

    const outputDir = path.join(STORAGE_PATH, 'output', jobId);
    await fsPromises.mkdir(outputDir, { recursive: true });

    const payload: ConversionJobPayload = {
      job_id: jobId,
      input_path: hash['input_path'],
      output_dir: outputDir,
      kcc_workers: kccWorkers,
      options: {
        device, format: fmt,
        manga: options.manga ?? false,
        hq: options.hq ?? false,
        webtoon: options.webtoon ?? false,
        two_panel: options.two_panel ?? false,
        upscale: options.upscale ?? false,
      },
    };

    const queue = tier === ConversionTier.SMALL ? this.smallQueue
               : tier === ConversionTier.MEDIUM ? this.mediumQueue
               : this.largeQueue;

    const bullJob = await queue.add('convert', payload);

    await this.redis.setJobHash(jobId, {
      status: JobStatus.QUEUED,
      format: fmt,
      device,
      page_count: pageCount,
      eta_s: etaS,
      output_dir: outputDir,
      queued_at: new Date().toISOString(),
    });

    const queuePos = await queue.getWaitingCount();

    this.logger.log(`Finalized job=${jobId} tier=${tier} eta=${etaS}s bullId=${bullJob.id}`);
    return { job_id: jobId, eta_s: etaS, queue_position: queuePos };
  }

  async getJob(jobId: string): Promise<Record<string, unknown>> {
    const hash = await this.redis.getJobHash(jobId);
    if (hash && Object.keys(hash).length > 0) {
      return this.formatJob(jobId, hash);
    }
    // Fallback to Postgres/SQLite for terminal jobs
    const dbJob = await this.repo.findById(jobId);
    if (!dbJob) throw new NotFoundException();
    return dbJob as unknown as Record<string, unknown>;
  }

  async cancelJob(jobId: string): Promise<void> {
    const hash = await this.redis.getJobHash(jobId);
    if (!hash || !hash['status']) throw new NotFoundException();
    const terminalStatuses: string[] = [
      JobStatus.COMPLETE,
      JobStatus.DOWNLOADED,
      JobStatus.ERRORED,
      JobStatus.CANCELLED,
    ];
    if (terminalStatuses.includes(hash['status'])) {
      throw new ConflictException('already_terminal');
    }
    // Remove from queue if still queued
    for (const queue of [this.smallQueue, this.mediumQueue, this.largeQueue]) {
      const waiting = await queue.getWaiting();
      for (const j of waiting) {
        if (j.data?.job_id === jobId) await j.remove();
      }
    }
    await this.redis.setJobHash(jobId, { status: JobStatus.CANCELLED });
  }

  streamProgress(jobId: string, res: Response): void {
    res.setHeader('Content-Type', 'text/event-stream');
    res.setHeader('Cache-Control', 'no-cache');
    res.setHeader('Connection', 'keep-alive');
    res.setHeader('Access-Control-Allow-Origin', '*');
    res.flushHeaders();

    const send = (data: unknown) => res.write(`data: ${JSON.stringify(data)}\n\n`);

    // Send current state immediately
    this.redis.getJobHash(jobId).then((hash) => {
      if (hash && Object.keys(hash).length > 0) send(this.formatJob(jobId, hash));
    });

    const channel = `jobs:${jobId}:progress`;
    this.redis.subscriber.subscribe(channel, (err) => {
      if (err) { res.end(); return; }
    });

    const onMessage = (_ch: string, message: string) => {
      try { send(JSON.parse(message)); } catch { /* ignore */ }
    };

    this.redis.subscriber.on('message', onMessage);

    res.on('close', () => {
      this.redis.subscriber.unsubscribe(channel);
      this.redis.subscriber.off('message', onMessage);
    });
  }

  private formatJob(jobId: string, hash: Record<string, string>): Record<string, unknown> {
    return {
      id: jobId,
      status: hash['status'],
      filename: hash['filename'],
      output_filename: hash['output_filename'] ?? null,
      format: hash['format'] ?? null,
      device: hash['device'] ?? null,
      page_count: hash['page_count'] ? parseInt(hash['page_count']) : null,
      file_size_bytes: hash['file_size_bytes'] ? parseInt(hash['file_size_bytes']) : null,
      output_size_bytes: hash['output_size_bytes'] ? parseInt(hash['output_size_bytes']) : null,
      eta_s: hash['eta_s'] ? parseFloat(hash['eta_s']) : null,
      elapsed_s: hash['elapsed_s'] ? parseFloat(hash['elapsed_s']) : null,
      error_message: hash['error_message'] ?? null,
      phase: hash['phase'] ?? null,
      progress: hash['progress'] ? parseInt(hash['progress']) : null,
      created_at: hash['created_at'] ?? null,
      queued_at: hash['queued_at'] ?? null,
      processing_at: hash['processing_at'] ?? null,
      completed_at: hash['completed_at'] ?? null,
      output_path: hash['output_path'] ?? null,
      download_url: hash['output_path'] ? `/api/jobs/${jobId}/download` : null,
    };
  }
}
