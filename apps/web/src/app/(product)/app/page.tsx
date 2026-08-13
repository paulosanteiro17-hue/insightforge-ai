import { resolveAppDestination } from "@runtime-server-bootstrap";

export default async function AppResolverPage() {
  await resolveAppDestination();
}
