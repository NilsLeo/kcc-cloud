import { Module } from '@nestjs/common';
import { BullModule } from '@nestjs/bullmq';
import { ConversionModule } from './conversion/conversion.module';
import { QUEUE_NAMES } from '@mgc/queue';

@Module({
  imports: [
    BullModule.forRoot({
      connection: { url: process.env.REDIS_URL ?? 'redis://localhost:6379' },
    }),
    BullModule.registerQueue(
      { name: QUEUE_NAMES.SMALL,  defaultJobOptions: { attempts: 1 } },
      { name: QUEUE_NAMES.MEDIUM, defaultJobOptions: { attempts: 1 } },
      { name: QUEUE_NAMES.LARGE,  defaultJobOptions: { attempts: 1 } },
    ),
    ConversionModule,
  ],
})
export class WorkerModule {}
