import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { RangeFilter } from "@/components/dashboard/range-filter";

const { replace } = vi.hoisted(() => ({ replace: vi.fn() }));

vi.mock("next/navigation", () => ({
  useRouter: () => ({ replace }),
  usePathname: () => "/app/northstar-commerce/overview",
  useSearchParams: () =>
    new URLSearchParams("range=30d&compare=previous_period")
}));

describe("RangeFilter", () => {
  beforeEach(() => replace.mockReset());

  it("announces the selected range and updates canonical URL state", async () => {
    const user = userEvent.setup();
    render(<RangeFilter value="30d" />);

    expect(
      screen.getByRole("button", { name: "Last 30 days" })
    ).toHaveAttribute("aria-pressed", "true");

    await user.click(screen.getByRole("button", { name: "Last 90 days" }));

    expect(replace).toHaveBeenCalledWith(
      "/app/northstar-commerce/overview?range=90d&compare=previous_period",
      { scroll: false }
    );
  });
});
