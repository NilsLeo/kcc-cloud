export interface IStorageProvider {
  putObject(key: string, body: Buffer | NodeJS.ReadableStream, contentType: string): Promise<void>;
  getPresignedUploadUrl(key: string, expiresIn: number): Promise<string>;
  getPresignedDownloadUrl(key: string, expiresIn: number): Promise<string>;
  deleteObject(key: string): Promise<void>;
}
