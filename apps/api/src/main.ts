import 'reflect-metadata';
import { NestFactory } from '@nestjs/core';
import { ValidationPipe } from '@nestjs/common';
import { AppModule } from './app.module';

async function bootstrap() {
  const app = await NestFactory.create(AppModule);
  app.enableCors({ origin: '*' });
  app.useGlobalPipes(new ValidationPipe({ transform: true, whitelist: true }));
  const port = parseInt(process.env.PORT ?? '3000', 10);
  await app.listen(port);
  console.log(`API listening on port ${port}`);
}

bootstrap().catch(console.error);
