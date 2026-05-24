import { Injectable, OnModuleDestroy, OnModuleInit, Logger } from '@nestjs/common';
import Redis from 'ioredis';

@Injectable()
export class RedisService implements OnModuleInit, OnModuleDestroy {
  private readonly logger = new Logger(RedisService.name);
  private client!: Redis;
  private publisher!: Redis;

  onModuleInit() {
    const url = process.env.REDIS_URL ?? 'redis://localhost:6379';
    this.client = new Redis(url, { lazyConnect: true });
    this.publisher = new Redis(url, { lazyConnect: true });
  }

  async onModuleDestroy() {
    await this.client.quit();
    await this.publisher.quit();
  }

  async updateJobHash(jobId: string, fields: Record<string, string | number>): Promise<void> {
    const key = `job:${jobId}`;
    const args: (string | number)[] = [];
    for (const [k, v] of Object.entries(fields)) {
      args.push(k, String(v));
    }
    if (args.length) await this.client.hset(key, ...args);
  }

  async publishProgress(jobId: string, payload: Record<string, unknown>): Promise<void> {
    const channel = `jobs:${jobId}:progress`;
    await this.publisher.publish(channel, JSON.stringify(payload));
  }

  async setJobTtl(jobId: string, ttlSeconds: number): Promise<void> {
    await this.client.expire(`job:${jobId}`, ttlSeconds);
  }
}
