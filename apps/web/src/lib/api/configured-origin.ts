const LOCAL_API_ORIGIN = "http://127.0.0.1:8000";
const LOCAL_WEB_ORIGIN = "http://localhost:3000";

function exactHttpOrigin(value: string, variableName: string): string {
  let parsed: URL;
  try {
    parsed = new URL(value);
  } catch {
    throw new Error(
      `${variableName} must be an absolute HTTP or HTTPS origin.`
    );
  }

  if (
    !["http:", "https:"].includes(parsed.protocol) ||
    parsed.username ||
    parsed.password ||
    parsed.pathname !== "/" ||
    parsed.search ||
    parsed.hash
  ) {
    throw new Error(
      `${variableName} must be an exact HTTP or HTTPS origin without credentials, a path, query, or fragment.`
    );
  }

  return parsed.origin;
}

export function configuredApiOrigin(
  value = process.env.API_INTERNAL_URL
): string {
  return exactHttpOrigin(value?.trim() || LOCAL_API_ORIGIN, "API_INTERNAL_URL");
}

export function configuredWebOrigin(
  value = process.env.PUBLIC_WEB_URL
): string {
  return exactHttpOrigin(value?.trim() || LOCAL_WEB_ORIGIN, "PUBLIC_WEB_URL");
}
