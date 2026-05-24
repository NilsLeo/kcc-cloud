import { Controller, Get } from '@nestjs/common';

@Controller('api/admin')
export class AdminController {
  @Get('health')
  health() { return { status: 'ok' }; }
}
