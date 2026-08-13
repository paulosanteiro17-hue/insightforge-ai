import { describe, expect, it } from "vitest";
import {
  configuredApiOrigin,
  configuredWebOrigin
} from "@/lib/api/configured-origin";

describe("trusted server origins", () => {
  it("uses fixed local origins when environment values are absent", () => {
    expect(configuredApiOrigin("")).toBe("http://127.0.0.1:8000");
    expect(configuredWebOrigin("")).toBe("http://localhost:3000");
  });

  it("normalizes exact configured origins", () => {
    expect(configuredApiOrigin("https://api.example.com/")).toBe(
      "https://api.example.com"
    );
    expect(configuredWebOrigin("https://app.example.com")).toBe(
      "https://app.example.com"
    );
  });

  it.each([
    "file:///etc/passwd",
    "https://user:secret@example.com",
    "https://example.com/api",
    "https://example.com?redirect=internal",
    "//attacker.example"
  ])("rejects unsafe upstream values: %s", (value) => {
    expect(() => configuredApiOrigin(value)).toThrow(
      /must be an (absolute|exact) HTTP or HTTPS origin/
    );
  });
});
