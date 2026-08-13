import { createLiveAdminApi } from "@/lib/api/live-admin-adapter";
import { createLiveCoreApi } from "@/lib/api/live-core-adapter";
import { createLiveImportsApi } from "@/lib/api/live-imports-adapter";
import { createLiveIntelligenceApi } from "@/lib/api/live-intelligence-adapter";
import type { InsightForgeApi } from "@/lib/api/contracts";
import { ApiHttpClient } from "@/lib/api/http-client";

const client = new ApiHttpClient();

const core = createLiveCoreApi(client);
const admin = createLiveAdminApi(client);
const intelligence = createLiveIntelligenceApi(client);

export const insightForgeApi: InsightForgeApi = {
  ...core,
  ...admin,
  ...intelligence,
  imports: createLiveImportsApi(client)
};

export { client as insightForgeHttpClient };
