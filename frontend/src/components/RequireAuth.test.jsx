import { render, screen } from "@testing-library/react";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { beforeEach, describe, expect, it, vi } from "vitest";
import RequireAuth from "./RequireAuth";
import { getCurrentStudent } from "../hooks/useAuth";

vi.mock("../hooks/useAuth", () => ({
  clearAuthSession: vi.fn(),
  getCurrentStudent: vi.fn(),
  getToken: vi.fn(() => "session"),
  isAuthenticated: vi.fn(() => true),
  wasExplicitlyLoggedOut: vi.fn(() => false),
}));
vi.mock("../services/api", () => ({ authMe: vi.fn() }));
vi.mock("../services/profile", () => ({ setSelectedProfile: vi.fn() }));

describe("RequireAuth password-change gate", () => {
  beforeEach(() => vi.clearAllMocks());

  it("redirects a forced-change student away from a protected route", async () => {
    getCurrentStudent.mockReturnValue({ id: 7, name: "Fresh", must_change_password: true });
    render(
      <MemoryRouter initialEntries={["/learning-path"]}>
        <Routes>
          <Route path="/learning-path" element={<RequireAuth><p>Protected content</p></RequireAuth>} />
          <Route path="/change-password" element={<p>Change password destination</p>} />
        </Routes>
      </MemoryRouter>,
    );

    expect(await screen.findByText("Change password destination")).toBeInTheDocument();
    expect(screen.queryByText("Protected content")).not.toBeInTheDocument();
  });

  it("does not let a completed student return to the first-login page", async () => {
    getCurrentStudent.mockReturnValue({ id: 7, name: "Returning", must_change_password: false });
    render(
      <MemoryRouter initialEntries={["/change-password"]}>
        <Routes>
          <Route path="/change-password" element={<RequireAuth passwordChangeOnly><p>Password form</p></RequireAuth>} />
          <Route path="/" element={<p>Today destination</p>} />
        </Routes>
      </MemoryRouter>,
    );

    expect(await screen.findByText("Today destination")).toBeInTheDocument();
    expect(screen.queryByText("Password form")).not.toBeInTheDocument();
  });
});
