import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { beforeEach, describe, expect, it, vi } from "vitest";
import LoginPage from "./LoginPage";
import { authLogin } from "../services/api";

vi.mock("../services/api", () => ({ authLogin: vi.fn() }));
vi.mock("../hooks/useAuth", () => ({
  clearToken: vi.fn(),
  getCurrentStudent: vi.fn(() => null),
  isAuthenticated: vi.fn(() => false),
  setToken: vi.fn(),
}));
vi.mock("../services/profile", () => ({
  clearSelectedProfile: vi.fn(),
  setSelectedProfile: vi.fn(),
}));

describe("LoginPage first-login routing", () => {
  beforeEach(() => vi.clearAllMocks());

  it("sends a student who must change their password to the change page", async () => {
    authLogin.mockResolvedValue({
      access_token: "temporary-session",
      student_id: 7,
      name: "Fresh Student",
      email: "fresh@example.test",
      is_mentor: false,
      must_change_password: true,
    });
    render(
      <MemoryRouter initialEntries={["/login?next=/learning-path"]}>
        <Routes>
          <Route path="/login" element={<LoginPage />} />
          <Route path="/change-password" element={<p>Change password destination</p>} />
          <Route path="/learning-path" element={<p>Learning path destination</p>} />
        </Routes>
      </MemoryRouter>,
    );

    fireEvent.change(screen.getByLabelText("Username"), { target: { value: "fresh" } });
    fireEvent.change(screen.getByLabelText("Password"), { target: { value: "TemporaryPass123!" } });
    fireEvent.click(screen.getByRole("button", { name: "Login" }));

    expect(await screen.findByText("Change password destination")).toBeInTheDocument();
    expect(screen.queryByText("Learning path destination")).not.toBeInTheDocument();
  });
});
