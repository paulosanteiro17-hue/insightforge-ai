import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { AuthForm } from "@/components/auth/auth-form";
import { TestProviders } from "@/test/test-providers";

const { replace } = vi.hoisted(() => ({ replace: vi.fn() }));

vi.mock("next/navigation", () => ({
  useRouter: () => ({ replace }),
  useSearchParams: () => new URLSearchParams()
}));

describe("AuthForm", () => {
  beforeEach(() => replace.mockReset());

  it("shows accessible validation before sending an invalid sign-in request", async () => {
    const user = userEvent.setup();
    render(<AuthForm mode="sign-in" />, { wrapper: TestProviders });

    await user.click(screen.getByRole("button", { name: "Sign in" }));

    expect(
      screen.getByText("Enter a valid email address.")
    ).toBeInTheDocument();
    expect(screen.getByText("Use at least 12 characters.")).toBeInTheDocument();
    expect(screen.getByLabelText("Work email")).toHaveAttribute(
      "aria-invalid",
      "true"
    );
    expect(replace).not.toHaveBeenCalled();
  });

  it("routes a valid mock sign-in to the seeded organization overview", async () => {
    const user = userEvent.setup();
    render(<AuthForm mode="sign-in" />, { wrapper: TestProviders });

    await user.type(
      screen.getByLabelText("Work email"),
      "jordan@northstar.example"
    );
    await user.type(screen.getByLabelText("Password"), "clear-signals-2026");
    await user.click(screen.getByRole("button", { name: "Sign in" }));

    await waitFor(() => {
      expect(replace).toHaveBeenCalledWith("/app/northstar-commerce/overview");
    });
  });
});
