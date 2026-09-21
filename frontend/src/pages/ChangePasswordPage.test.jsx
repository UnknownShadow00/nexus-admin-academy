import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import ChangePasswordPage from "./ChangePasswordPage";
import { authChangePassword } from "../services/api";

vi.mock("../services/api", () => ({ authChangePassword: vi.fn(), authLogout: vi.fn() }));
vi.mock("../hooks/useAuth", () => ({ clearAuthSession: vi.fn(), setToken: vi.fn() }));
vi.mock("../services/profile", () => ({ setSelectedProfile: vi.fn() }));

describe("ChangePasswordPage", () => {
  beforeEach(() => vi.clearAllMocks());
  afterEach(cleanup);

  it("validates confirmation before sending a password", async () => {
    render(<MemoryRouter><ChangePasswordPage /></MemoryRouter>);
    fireEvent.change(screen.getByLabelText("New password"), { target: { value: "NewPermanentPass123!" } });
    fireEvent.change(screen.getByLabelText("Confirm new password"), { target: { value: "DifferentPass123!" } });
    fireEvent.click(screen.getByRole("button", { name: "Change password" }));

    expect(await screen.findByRole("alert")).toHaveTextContent("Passwords do not match");
    expect(authChangePassword).not.toHaveBeenCalled();
  });

  it("rotates the session and sends the student to Today", async () => {
    authChangePassword.mockResolvedValue({
      access_token: "rotated-session",
      student_id: 7,
      name: "Fresh Student",
      email: "fresh@example.test",
      is_mentor: false,
      must_change_password: false,
    });
    render(
      <MemoryRouter initialEntries={["/change-password"]}>
        <Routes>
          <Route path="/change-password" element={<ChangePasswordPage />} />
          <Route path="/" element={<p>Today destination</p>} />
        </Routes>
      </MemoryRouter>,
    );
    fireEvent.change(screen.getByLabelText("New password"), { target: { value: "NewPermanentPass123!" } });
    fireEvent.change(screen.getByLabelText("Confirm new password"), { target: { value: "NewPermanentPass123!" } });
    fireEvent.click(screen.getByRole("button", { name: "Change password" }));

    await waitFor(() => expect(authChangePassword).toHaveBeenCalledWith({
      new_password: "NewPermanentPass123!",
      confirm_password: "NewPermanentPass123!",
    }, { suppressToast: true }));
    expect(await screen.findByText("Today destination")).toBeInTheDocument();
  });

  it("shows the backend password-policy reason", async () => {
    authChangePassword.mockRejectedValue({
      userMessage: "Password cannot begin or end with whitespace.",
    });
    render(<MemoryRouter><ChangePasswordPage /></MemoryRouter>);
    fireEvent.change(screen.getByLabelText("New password"), { target: { value: " NewPermanentPass123!" } });
    fireEvent.change(screen.getByLabelText("Confirm new password"), { target: { value: " NewPermanentPass123!" } });
    fireEvent.click(screen.getByRole("button", { name: "Change password" }));

    expect(await screen.findByRole("alert")).toHaveTextContent("Password cannot begin or end with whitespace.");
  });
});
