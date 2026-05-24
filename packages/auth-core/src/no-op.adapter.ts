import { IAuthProvider, AuthContext } from '@mgc/core';

export class NoOpAuthProvider implements IAuthProvider {
  async verify(_token: string): Promise<AuthContext> {
    return { userId: null, isAuthenticated: false };
  }

  async getUserId(_token: string): Promise<string | null> {
    return null;
  }
}
