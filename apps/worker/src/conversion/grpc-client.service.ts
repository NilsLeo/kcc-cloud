import { Injectable, Logger, OnModuleInit } from '@nestjs/common';
import * as grpc from '@grpc/grpc-js';
import * as protoLoader from '@grpc/proto-loader';
import * as path from 'path';

const PROTO_PATH = path.resolve(
  __dirname,
  '../../../../worker-kcc/proto/conversion.proto',
);

@Injectable()
export class GrpcClientService implements OnModuleInit {
  private readonly logger = new Logger(GrpcClientService.name);
  private client: any;

  onModuleInit() {
    const packageDef = protoLoader.loadSync(PROTO_PATH, {
      keepCase: true,
      longs: String,
      enums: String,
      defaults: true,
      oneofs: true,
    });
    const proto = grpc.loadPackageDefinition(packageDef) as any;
    const addr = process.env.KCC_GRPC_ADDR ?? 'localhost:50051';
    this.client = new proto.conversion.Converter(addr, grpc.credentials.createInsecure());
    this.logger.log(`gRPC client connected to ${addr}`);
  }

  convert(request: {
    job_id: string;
    input_path: string;
    output_dir: string;
    format: string;
    device: string;
    kcc_workers: number;
    manga: boolean;
    hq: boolean;
    webtoon: boolean;
    two_panel: boolean;
    upscale: boolean;
  }): AsyncIterable<{
    job_id: string;
    phase: string;
    progress: number;
    status: string;
    message: string;
    output_path: string;
  }> {
    const call = this.client.Convert(request);
    return {
      [Symbol.asyncIterator]() {
        return {
          next(): Promise<IteratorResult<any>> {
            return new Promise((resolve, reject) => {
              call.once('data', (data: any) => resolve({ value: data, done: false }));
              call.once('end', () => resolve({ value: undefined, done: true }));
              call.once('error', (err: any) => reject(err));
            });
          },
          return(): Promise<IteratorResult<any>> {
            call.cancel();
            return Promise.resolve({ value: undefined, done: true });
          },
        };
      },
    };
  }

  cancel(jobId: string): Promise<{ success: boolean; message: string }> {
    return new Promise((resolve, reject) => {
      this.client.Cancel({ job_id: jobId }, (err: any, response: any) => {
        if (err) return reject(err);
        resolve(response);
      });
    });
  }
}
