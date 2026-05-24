export interface IEventBus {
  emit(event: string, payload: unknown): Promise<void>;
  subscribe(event: string, handler: (payload: unknown) => void | Promise<void>): void;
}
