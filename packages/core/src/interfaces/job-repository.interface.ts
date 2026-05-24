import { Job } from '../entities/job.entity';

export interface IJobRepository {
  create(data: Omit<Job, 'id' | 'created_at'>): Promise<Job>;
  findById(id: string): Promise<Job | null>;
  saveTerminal(id: string, data: Partial<Job>): Promise<void>;
  listByUser(userId: string, page: number, limit: number): Promise<{ jobs: Job[]; total: number }>;
}
