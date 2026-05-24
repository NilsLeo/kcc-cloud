import { Module } from '@nestjs/common';
import { BullModule } from '@nestjs/bullmq';
import { QUEUE_NAMES } from '@mgc/queue';
import { ConversionController } from './conversion.controller';
import { ConversionService } from './conversion.service';
import { RedisService } from '../redis/redis.service';

@Module({
  imports: [
    BullModule.registerQueue(
      { name: QUEUE_NAMES.SMALL },
      { name: QUEUE_NAMES.MEDIUM },
      { name: QUEUE_NAMES.LARGE },
    ),
  ],
  controllers: [ConversionController],
  providers: [ConversionService, RedisService],
})
export class ConversionModule {}
