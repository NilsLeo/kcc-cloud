import { Injectable, OnModuleDestroy, OnModuleInit } from '@nestjs/common';
import Redis from 'ioredis';

@Injectable()
export class RedisService implements OnModuleInit, OnModuleDestroy {
  client!: Redis;
  subscriber!: Redis;

  onModuleInit() {
    const url = process.env.REDIS_URL ?? 'redis://localhost:6379';
    this.client = new Redis(url);
    this.subscriber = new Redis(url);
  }

  async onModuleDestroy() {
    await this.client.quit();
    await this.subscriber.quit();
  }

  async getJobHash(jobId: string): Promise<Record<string, string>> {
    return this.client.hgetall(`job:${jobId}`);
  }

  async setJobHash(jobId: string, fields: Record<string, string | number>): Promise<void> {
    const args: (string | number)[] = [];
    for (const [k, v] of Object.entries(fields)) args.push(k, String(v));
    if (args.length) await this.client.hset(`job:${jobId}`, ...args);
  }

  async deleteJobHash(jobId: string): Promise<void> {
    await this.client.del(`job:${jobId}`);
  }
}
