export interface AuthContext {
  userId: string | null;
  isAuthenticated: boolean;
}

export interface IAuthProvider {
  verify(token: string): Promise<AuthContext>;
  getUserId(token: string): Promise<string | null>;
}
