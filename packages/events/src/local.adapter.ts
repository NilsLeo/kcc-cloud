import EventEmitter2 from 'eventemitter2';
import { IEventBus } from '@mgc/core';

export class EventEmitter2LocalAdapter implements IEventBus {
  private readonly emitter = new EventEmitter2({ wildcard: true });

  async emit(event: string, payload: unknown): Promise<void> {
    this.emitter.emit(event, payload);
  }

  subscribe(event: string, handler: (payload: unknown) => void | Promise<void>): void {
    this.emitter.on(event, handler);
  }
}
