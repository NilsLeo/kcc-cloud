import { Module } from '@nestjs/common';
import { BullModule } from '@nestjs/bullmq';
import { ThrottlerModule } from '@nestjs/throttler';
import { QUEUE_NAMES } from '@mgc/queue';
import { ConversionModule } from './conversion/conversion.module';
import { AdminModule } from './admin/admin.module';

@Module({
  imports: [
    ThrottlerModule.forRoot([{
      name: 'global',
      ttl: parseInt(process.env.THROTTLE_TTL ?? '60') * 1000,
      limit: parseInt(process.env.THROTTLE_LIMIT ?? '100'),
    }]),
    BullModule.forRoot({
      connection: { url: process.env.REDIS_URL ?? 'redis://localhost:6379' },
    }),
    BullModule.registerQueue(
      { name: QUEUE_NAMES.SMALL },
      { name: QUEUE_NAMES.MEDIUM },
      { name: QUEUE_NAMES.LARGE },
    ),
    ConversionModule,
    AdminModule,
  ],
})
export class AppModule {}
