import { IJobRepository, Job } from '@mgc/core';

export class BaseJobRepository implements IJobRepository {
  private prisma: any;

  constructor(databaseUrl: string) {
    // Lazy import so the module doesn't crash if Prisma isn't generated yet
    try {
      // eslint-disable-next-line @typescript-eslint/no-var-requires
      const { PrismaClient } = require('.prisma/base-client');
      this.prisma = new PrismaClient({ datasources: { db: { url: databaseUrl } } });
    } catch {
      this.prisma = null;
    }
  }

  async create(data: Omit<Job, 'id' | 'created_at'>): Promise<Job> {
    if (!this.prisma) throw new Error('Prisma base client not generated — run pnpm db:generate');
    return this.prisma.job.create({ data: this._toDb(data) }) as unknown as Job;
  }

  async findById(id: string): Promise<Job | null> {
    if (!this.prisma) return null;
    return this.prisma.job.findUnique({ where: { id } }) as unknown as Job | null;
  }

  async saveTerminal(id: string, data: Partial<Job>): Promise<void> {
    if (!this.prisma) return;
    await this.prisma.job.upsert({
      where: { id },
      create: { id, status: data.status ?? 'ERRORED', filename: data.filename ?? '', ...this._toDb(data) },
      update: this._toDb(data),
    });
  }

  async listByUser(_userId: string, page: number, limit: number): Promise<{ jobs: Job[]; total: number }> {
    if (!this.prisma) return { jobs: [], total: 0 };
    const [jobs, total] = await Promise.all([
      this.prisma.job.findMany({ skip: page * limit, take: limit, orderBy: { created_at: 'desc' } }),
      this.prisma.job.count(),
    ]);
    return { jobs: jobs as unknown as Job[], total };
  }

  private _toDb(data: Partial<Job>): Record<string, unknown> {
    const d: Record<string, unknown> = { ...data };
    // BigInt columns
    if (d.file_size_bytes != null) d.file_size_bytes = BigInt(d.file_size_bytes as number);
    if (d.output_size_bytes != null) d.output_size_bytes = BigInt(d.output_size_bytes as number);
    return d;
  }
}
