import { describe, it, expect, vi, beforeEach } from "vitest";
import { screen, waitFor, fireEvent } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { Login } from "../pages/Login";
import { renderWithProviders, mockUser } from "./test-utils";
import api from "../services/api";
import { useAuthStore } from "../store/useAuthStore";

// Mock the API module
vi.mock("../services/api", () => {
  return {
    default: {
      get: vi.fn(),
      post: vi.fn(),
    },
  };
});

describe("LoginPage Component Tests", () => {
  const user = userEvent.setup();

  beforeEach(() => {
    vi.clearAllMocks();
    useAuthStore.setState({
      user: null,
      token: null,
      refreshToken: null,
      isAuthenticated: false,
      isLoading: false,
    });
    // Default mock for oauth-config
    vi.mocked(api.get).mockResolvedValue({ data: { google_client_id: "test-client-id" } });
  });

  it("renders the login form with email, password fields and sign-in button", () => {
    renderWithProviders(<Login />);

    expect(screen.getByRole("heading", { name: /Welcome Back/i })).toBeInTheDocument();
    expect(screen.getByPlaceholderText(/name@company.com/i)).toBeInTheDocument();
    expect(screen.getByPlaceholderText(/••••••••/i)).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /Sign In/i })).toBeInTheDocument();
  });

  it("submits the form and calls the login API with valid credentials", async () => {
    vi.mocked(api.post).mockResolvedValueOnce({
      data: {
        access_token: "mock-access-token",
        refresh_token: "mock-refresh-token",
        requires_2fa: false,
      },
    });

    vi.mocked(api.get).mockImplementation(async (url: string) => {
      if (url === "/auth/me") {
        return { data: mockUser };
      }
      return { data: { google_client_id: "test-client-id" } };
    });

    renderWithProviders(<Login />);

    const emailInput = screen.getByPlaceholderText(/name@company.com/i);
    const passwordInput = screen.getByPlaceholderText(/••••••••/i);

    fireEvent.change(emailInput, { target: { value: "lawyer@example.com" } });
    fireEvent.change(passwordInput, { target: { value: "SecurePass123!" } });

    const submitBtn = screen.getByRole("button", { name: /Sign In/i });
    fireEvent.click(submitBtn);

    await waitFor(() => {
      expect(api.post).toHaveBeenCalledWith("/auth/login", {
        email: "lawyer@example.com",
        password: "SecurePass123!",
      });
    });

    await waitFor(() => {
      expect(useAuthStore.getState().isAuthenticated).toBe(true);
      expect(useAuthStore.getState().user?.email).toBe("lawyer@example.com");
    });
  });

  it("transitions to Email OTP step when 2FA is required by backend", async () => {
    vi.mocked(api.post).mockResolvedValueOnce({
      data: {
        requires_2fa: true,
        pending_2fa_token: "pending-2fa-token-12345",
        message: "A 6-digit OTP has been sent to l***r@example.com",
      },
    });

    renderWithProviders(<Login />);

    const emailInput = screen.getByPlaceholderText(/name@company.com/i);
    const passwordInput = screen.getByPlaceholderText(/••••••••/i);

    fireEvent.change(emailInput, { target: { value: "lawyer@example.com" } });
    fireEvent.change(passwordInput, { target: { value: "SecurePass123!" } });

    const submitBtn = screen.getByRole("button", { name: /Sign In/i });
    fireEvent.click(submitBtn);

    await waitFor(() => {
      expect(screen.getByText(/Two-Factor Authentication/i)).toBeInTheDocument();
      expect(screen.getByText(/A 6-digit OTP has been sent/i)).toBeInTheDocument();
    });

    // Verify 6 OTP input digits are rendered
    const otpInputs = screen.getAllByRole("textbox");
    expect(otpInputs.length).toBe(6);
  });

  it("displays an error message when login fails with invalid credentials", async () => {
    vi.mocked(api.post).mockRejectedValueOnce({
      response: {
        data: {
          detail: "Invalid email or password. Please try again.",
        },
      },
    });

    renderWithProviders(<Login />);

    const emailInput = screen.getByPlaceholderText(/name@company.com/i);
    const passwordInput = screen.getByPlaceholderText(/••••••••/i);

    fireEvent.change(emailInput, { target: { value: "wrong@example.com" } });
    fireEvent.change(passwordInput, { target: { value: "WrongPassword" } });

    const submitBtn = screen.getByRole("button", { name: /Sign In/i });
    fireEvent.click(submitBtn);

    await waitFor(() => {
      expect(screen.getByText(/Invalid email or password. Please try again./i)).toBeInTheDocument();
    });
  });

  it("displays session expired alert banner when ?expired=true is present in query parameters", () => {
    renderWithProviders(<Login />, {
      initialEntries: ["/login?expired=true"],
    });

    expect(
      screen.getByText(/Your session expired due to inactivity. Please sign in again./i)
    ).toBeInTheDocument();
  });

  it("toggles password visibility when the show/hide password icon is clicked", async () => {
    renderWithProviders(<Login />);

    const passwordInput = screen.getByPlaceholderText(/••••••••/i) as HTMLInputElement;
    expect(passwordInput.type).toBe("password");

    const toggleBtn = screen.getByRole("button", { name: /Toggle password visibility/i });
    await user.click(toggleBtn);

    expect(passwordInput.type).toBe("text");

    await user.click(toggleBtn);
    expect(passwordInput.type).toBe("password");
  });
});
