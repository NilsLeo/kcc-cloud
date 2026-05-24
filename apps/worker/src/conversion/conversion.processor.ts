import { Processor, WorkerHost } from '@nestjs/bullmq';
import { Logger } from '@nestjs/common';
import { Job } from 'bullmq';
import * as path from 'path';
import * as fs from 'fs/promises';

import { QUEUE_NAMES, ConversionJobPayload } from '@mgc/queue';
import { JobStatus } from '@mgc/conversion-sdk';
import { GrpcClientService } from './grpc-client.service';
import { RedisService } from '../redis/redis.service';
import { EventEmitter2LocalAdapter } from '@mgc/events';
import { BaseJobRepository } from '@mgc/db';

const TTL_24H = 86_400;

const eventBus = new EventEmitter2LocalAdapter();
const repo = new BaseJobRepository(process.env.DATABASE_URL ?? 'file:/data/mgc.db');

abstract class BaseConversionProcessor extends WorkerHost {
  protected abstract readonly processorLogger: Logger;

  constructor(
    protected readonly grpc: GrpcClientService,
    protected readonly redis: RedisService,
  ) {
    super();
  }

  async process(job: Job<ConversionJobPayload>): Promise<void> {
    const { job_id, input_path, output_dir, kcc_workers, options } = job.data;
    this.processorLogger.log(`Processing job=${job_id}`);

    const processingAt = new Date().toISOString();
    await this.redis.updateJobHash(job_id, {
      status: JobStatus.PROCESSING,
      processing_at: processingAt,
      kcc_workers,
      input_path,
    });
    await this.redis.publishProgress(job_id, {
      phase: 'started', progress: 0, status: JobStatus.PROCESSING, message: 'Job started',
    });

    let outputPath = '';
    let lastPhase = 'mupdf';
    let lastErrorMessage = 'KCC conversion failed';

    try {
      const stream = this.grpc.convert({
        job_id,
        input_path,
        output_dir,
        format: options.format,
        device: options.device,
        kcc_workers,
        manga: options.manga,
        hq: options.hq,
        webtoon: options.webtoon,
        two_panel: options.two_panel,
        upscale: options.upscale,
      });

      for await (const event of stream) {
        lastPhase = event.phase;
        if (event.message) lastErrorMessage = event.message;

        await this.redis.updateJobHash(job_id, {
          phase: event.phase,
          progress: event.progress,
          status: event.status,
        });
        await this.redis.publishProgress(job_id, {
          phase: event.phase,
          progress: event.progress,
          status: event.status,
          message: event.message,
        });

        if (event.output_path) outputPath = event.output_path;

        if (['complete', 'error', 'cancelled'].includes(event.phase)) break;
      }
    } catch (err: unknown) {
      const message = err instanceof Error ? err.message : String(err);
      this.processorLogger.error(`gRPC error for job=${job_id}: ${message}`);
      await this.writeTerminal(job_id, JobStatus.ERRORED, { error_message: message });
      await eventBus.emit('events:job.failed', { job_id, error: message });
      return;
    }

    if (lastPhase === 'cancelled') {
      await this.writeTerminal(job_id, JobStatus.CANCELLED, {});
      await eventBus.emit('events:job.failed', { job_id, reason: 'cancelled' });
      return;
    }

    if (lastPhase === 'error') {
      await this.writeTerminal(job_id, JobStatus.ERRORED, { error_message: lastErrorMessage });
      await eventBus.emit('events:job.failed', { job_id, reason: 'kcc_error' });
      return;
    }

    const completedAt = new Date();
    const outputFilename = outputPath ? path.basename(outputPath) : null;
    let outputSizeBytes: number | null = null;
    if (outputPath) {
      try {
        const stat = await fs.stat(outputPath);
        outputSizeBytes = stat.size;
      } catch { /* ignore */ }
    }

    await this.redis.updateJobHash(job_id, {
      status: JobStatus.COMPLETE,
      phase: 'complete',
      progress: 100,
      output_path: outputPath,
      output_filename: outputFilename ?? '',
      output_size_bytes: outputSizeBytes != null ? String(outputSizeBytes) : '',
      completed_at: completedAt.toISOString(),
    });
    await this.redis.setJobTtl(job_id, TTL_24H);
    await this.redis.publishProgress(job_id, {
      phase: 'complete', progress: 100, status: JobStatus.COMPLETE, message: 'Done',
      output_filename: outputFilename,
      output_size: outputSizeBytes,
    });

    await this.writeTerminal(job_id, JobStatus.COMPLETE, {
      output_path: outputPath,
      output_filename: outputFilename,
      output_size_bytes: outputSizeBytes,
      completed_at: completedAt,
    });

    fs.unlink(input_path).catch(() => {});
    await eventBus.emit('events:job.completed', { job_id, output_path: outputPath });
    this.processorLogger.log(`Job ${job_id} completed → ${outputPath}`);
  }

  protected async writeTerminal(
    jobId: string,
    status: JobStatus,
    extra: Record<string, unknown>,
  ): Promise<void> {
    try {
      await repo.saveTerminal(jobId, { status, ...(extra as any) });
    } catch (err: unknown) {
      const message = err instanceof Error ? err.message : String(err);
      this.processorLogger.warn(`saveTerminal failed for ${jobId}: ${message}`);
    }
    const redisExtra: Record<string, string> = {};
    if (extra['error_message']) redisExtra['error_message'] = String(extra['error_message']);
    await this.redis.updateJobHash(jobId, { status, ...redisExtra });
    await this.redis.setJobTtl(jobId, TTL_24H);
  }
}

@Processor(QUEUE_NAMES.SMALL, { concurrency: 1 })
export class SmallProcessor extends BaseConversionProcessor {
  protected readonly processorLogger = new Logger(SmallProcessor.name);
  constructor(grpc: GrpcClientService, redis: RedisService) { super(grpc, redis); }
}

@Processor(QUEUE_NAMES.MEDIUM, { concurrency: 1 })
export class MediumProcessor extends BaseConversionProcessor {
  protected readonly processorLogger = new Logger(MediumProcessor.name);
  constructor(grpc: GrpcClientService, redis: RedisService) { super(grpc, redis); }
}

@Processor(QUEUE_NAMES.LARGE, { concurrency: 1 })
export class LargeProcessor extends BaseConversionProcessor {
  protected readonly processorLogger = new Logger(LargeProcessor.name);
  constructor(grpc: GrpcClientService, redis: RedisService) { super(grpc, redis); }
}

export { BaseConversionProcessor as ConversionProcessor };
