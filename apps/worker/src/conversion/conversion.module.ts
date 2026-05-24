import { Module } from '@nestjs/common';
import { SmallProcessor, MediumProcessor, LargeProcessor } from './conversion.processor';
import { GrpcClientService } from './grpc-client.service';
import { RedisService } from '../redis/redis.service';

@Module({
  providers: [SmallProcessor, MediumProcessor, LargeProcessor, GrpcClientService, RedisService],
})
export class ConversionModule {}
