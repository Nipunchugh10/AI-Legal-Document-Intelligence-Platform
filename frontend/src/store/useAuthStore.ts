import { create } from "zustand";
import api from "../services/api";

export interface User {
  id: number;
  email: string;
  is_active: boolean;
  created_at: string;
}

interface AuthState {
  user: User | null;
  token: string | null;
  isAuthenticated: boolean;
  isLoading: boolean;
  login: (token: string, user: User) => void;
  logout: () => void;
  setUser: (user: User | null) => void;
  checkAuth: () => Promise<User | null>;
}

export const useAuthStore = create<AuthState>((set, get) => ({
  user: null,
  token: localStorage.getItem("access_token"),
  isAuthenticated: !!localStorage.getItem("access_token"),
  isLoading: true,

  login: (token, user) => {
    localStorage.setItem("access_token", token);
    set({ token, user, isAuthenticated: true, isLoading: false });
  },

  logout: () => {
    localStorage.removeItem("access_token");
    set({ token: null, user: null, isAuthenticated: false, isLoading: false });
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
      // Interceptor will handle logout if it's a 401, but we clean up here too
      localStorage.removeItem("access_token");
      set({ token: null, user: null, isAuthenticated: false, isLoading: false });
      return null;
    }
  },
}));
