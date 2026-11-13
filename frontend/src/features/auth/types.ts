export type UserRole = 'ADMIN' | 'INVESTIGATOR' | 'OPERATOR' | 'VIEWER';

export interface AuthUser {
  id: string;
  username: string;
  displayName: string;
  role: UserRole;
}

export interface AuthState {
  user: AuthUser | null;
  isAuthenticated: boolean;
  isLoading: boolean;
  error: string | null;
}
