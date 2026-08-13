import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";
import { ImportPreviewPanel } from "@/components/imports/data-sources-page";

describe("ImportPreviewPanel", () => {
  it("allows confirmation only for a clean validation preview", async () => {
    const user = userEvent.setup();
    const onConfirm = vi.fn();
    render(
      <ImportPreviewPanel
        committing={false}
        onConfirm={onConfirm}
        preview={{
          import_id: "import-clean",
          kind: "customers",
          filename: "customers.csv",
          status: "ready",
          headers: ["external_id", "name"],
          preview_rows: [{ external_id: "CUS-1", name: "Avery Morgan" }],
          total_rows: 1,
          valid_rows: 1,
          error_rows: 0,
          errors: [],
          errors_truncated: false,
          duplicate_policy: "create_only"
        }}
      />
    );
    await user.click(screen.getByRole("button", { name: "Confirm import" }));
    expect(onConfirm).toHaveBeenCalledOnce();
    expect(
      screen.getByRole("table", { name: "CSV validation preview" })
    ).toBeInTheDocument();
  });

  it("shows structured errors and disables confirmation for an invalid file", () => {
    render(
      <ImportPreviewPanel
        committing={false}
        onConfirm={vi.fn()}
        preview={{
          import_id: "import-invalid",
          kind: "customers",
          filename: "bad.csv",
          status: "validation_failed",
          headers: ["external_id"],
          preview_rows: [],
          total_rows: 1,
          valid_rows: 0,
          error_rows: 1,
          errors: [
            {
              id: "error-1",
              row_number: 2,
              column: "email",
              code: "invalid_email",
              message: "Enter a valid email address."
            }
          ],
          errors_truncated: false,
          duplicate_policy: "create_only"
        }}
      />
    );
    expect(
      screen.getByText("invalid_email", { exact: false })
    ).toBeInTheDocument();
    expect(
      screen.getByRole("button", { name: "Confirm import" })
    ).toBeDisabled();
  });
});
