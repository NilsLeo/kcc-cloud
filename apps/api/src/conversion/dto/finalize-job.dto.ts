import { IsString, IsBoolean, IsOptional, IsObject, ValidateNested } from 'class-validator';
import { Type } from 'class-transformer';

class ConversionOptionsDto {
  @IsBoolean() @IsOptional() manga?: boolean;
  @IsBoolean() @IsOptional() hq?: boolean;
  @IsBoolean() @IsOptional() webtoon?: boolean;
  @IsBoolean() @IsOptional() two_panel?: boolean;
  @IsBoolean() @IsOptional() upscale?: boolean;
}

export class FinalizeJobDto {
  @IsString() device!: string;
  @IsString() format!: string;
  @IsOptional() @IsObject() @ValidateNested() @Type(() => ConversionOptionsDto) options?: ConversionOptionsDto;
}
