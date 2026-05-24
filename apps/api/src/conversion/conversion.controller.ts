import {
  Controller, Post, Get, Delete, Param, Body, Res,
  UploadedFile, UseInterceptors,
} from '@nestjs/common';
import { FileInterceptor } from '@nestjs/platform-express';
import { Response } from 'express';
import * as path from 'path';
import * as fs from 'fs';

import { ConversionService } from './conversion.service';
import { PrepareJobDto } from './dto/prepare-job.dto';
import { FinalizeJobDto } from './dto/finalize-job.dto';

@Controller('api/jobs')
export class ConversionController {
  constructor(private readonly svc: ConversionService) {}

  @Post('prepare')
  async prepare(@Body() dto: PrepareJobDto) {
    return this.svc.prepare(dto.filename, dto.size_bytes);
  }

  @Post(':id/upload')
  @UseInterceptors(FileInterceptor('file', { storage: undefined, limits: { fileSize: 2 * 1024 * 1024 * 1024 } }))
  async upload(@Param('id') id: string, @UploadedFile() file: Express.Multer.File) {
    await this.svc.upload(id, file);
    return { ok: true };
  }

  @Post(':id/finalize')
  async finalize(@Param('id') id: string, @Body() dto: FinalizeJobDto) {
    return this.svc.finalize(id, dto.device, dto.format, dto.options ?? {});
  }

  @Get(':id')
  async getJob(@Param('id') id: string) {
    return this.svc.getJob(id);
  }

  @Get(':id/progress')
  progress(@Param('id') id: string, @Res() res: Response) {
    this.svc.streamProgress(id, res);
  }

  @Get(':id/download')
  async download(@Param('id') id: string, @Res() res: Response) {
    const job = await this.svc.getJob(id) as Record<string, unknown>;
    const outputPath = job['output_path'] as string | null | undefined;
    const outputFilename = job['output_filename'] as string | null | undefined;
    if (!outputPath && !outputFilename) {
      return res.status(404).json({ error: 'not_ready' });
    }
    const storagePath = process.env.STORAGE_PATH ?? '/data/files';
    const filePath = outputPath ?? path.join(storagePath, 'output', id, outputFilename ?? '');
    if (!fs.existsSync(filePath)) return res.status(404).json({ error: 'file_not_found' });
    res.download(filePath, path.basename(filePath));
  }

  @Delete(':id')
  async cancel(@Param('id') id: string) {
    await this.svc.cancelJob(id);
    return { ok: true };
  }
}
