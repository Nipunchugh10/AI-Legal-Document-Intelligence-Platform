import { create } from "zustand";
import api from "../services/api";

export interface User {
  id: number;
  email: string;
  is_active: boolean;
  is_2fa_enabled: boolean;
  created_at: string;
}

interface AuthState {
  user: User | null;
  token: string | null;
  refreshToken: string | null;
  isAuthenticated: boolean;
  isLoading: boolean;
  login: (token: string, refreshToken: string, user: User) => void;
  logout: () => void;
  setUser: (user: User | null) => void;
  checkAuth: () => Promise<User | null>;
}

export const useAuthStore = create<AuthState>((set, get) => ({
  user: null,
  token: localStorage.getItem("access_token"),
  refreshToken: localStorage.getItem("refresh_token"),
  isAuthenticated: !!localStorage.getItem("access_token"),
  isLoading: true,

  login: (token, refreshToken, user) => {
    localStorage.setItem("access_token", token);
    localStorage.setItem("refresh_token", refreshToken);
    set({ token, refreshToken, user, isAuthenticated: true, isLoading: false });
  },

  logout: async () => {
    const refreshToken = localStorage.getItem("refresh_token");
    if (refreshToken) {
      try {
        await api.post("/auth/logout", { refresh_token: refreshToken });
      } catch (e) {
        console.error("Failed to revoke session on logout", e);
      }
    }
    localStorage.removeItem("access_token");
    localStorage.removeItem("refresh_token");
    set({ token: null, refreshToken: null, user: null, isAuthenticated: false, isLoading: false });
  },

  setUser: (user) => {
    set({ user });
  },

  checkAuth: async () => {
    const { token } = get();
    if (!token) {
      set({ isLoading: false, isAuthenticated: false, user: null });
      return null;
    }

    set({ isLoading: true });
    try {
      const response = await api.get<User>("/auth/me");
      const user = response.data;
      set({ user, isAuthenticated: true, isLoading: false });
      return user;
    } catch (error) {
      localStorage.removeItem("access_token");
      localStorage.removeItem("refresh_token");
      set({ token: null, refreshToken: null, user: null, isAuthenticated: false, isLoading: false });
      return null;
    }
  },
}));
