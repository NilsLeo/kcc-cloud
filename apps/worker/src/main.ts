import 'reflect-metadata';
import { NestFactory } from '@nestjs/core';
import { WorkerModule } from './worker.module';

async function bootstrap() {
  const app = await NestFactory.createApplicationContext(WorkerModule, {
    logger: ['log', 'warn', 'error'],
  });
  await app.init();
}

bootstrap().catch((err) => {
  console.error('Worker failed to start', err);
  process.exit(1);
});
