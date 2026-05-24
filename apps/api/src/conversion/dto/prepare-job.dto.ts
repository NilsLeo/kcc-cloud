import { IsString, IsNumber, Min, Max } from 'class-validator';
import { Type } from 'class-transformer';

export class PrepareJobDto {
  @IsString() filename!: string;
  @Type(() => Number) @IsNumber() @Min(1) @Max(2 * 1024 * 1024 * 1024) size_bytes!: number;
}
