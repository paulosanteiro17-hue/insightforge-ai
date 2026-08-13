import type * as Backend from "@/lib/api/backend-contracts";
import type {
  ImportHistoryRecord,
  ImportPreview,
  ImportTemplate,
  InsightForgeApi
} from "@/lib/api/contracts";
import { ApiHttpClient, pollUntil, sha256Hex } from "@/lib/api/http-client";

const importKinds: Backend.ImportKind[] = ["customers", "products", "orders"];

function parseCsvRow(row: string): string[] {
  const values: string[] = [];
  let value = "";
  let quoted = false;
  for (let index = 0; index < row.length; index += 1) {
    const character = row[index];
    if (character === '"' && quoted && row[index + 1] === '"') {
      value += '"';
      index += 1;
    } else if (character === '"') {
      quoted = !quoted;
    } else if (character === "," && !quoted) {
      values.push(value);
      value = "";
    } else {
      value += character;
    }
  }
  values.push(value);
  return values;
}

function templateFromCsv(
  kind: Backend.ImportKind,
  csv: string
): ImportTemplate {
  const rows = csv.trim().split(/\r?\n/).map(parseCsvRow);
  const headers = rows[0] ?? [];
  const labels: Record<Backend.ImportKind, string> = {
    customers: "Customers",
    products: "Products",
    orders: "Orders"
  };
  return {
    kind,
    name: `${labels[kind]} CSV`,
    description: `Import ${kind} using the canonical InsightForge columns.`,
    filename: `${kind}-template.csv`,
    headers,
    sample_rows: rows.slice(1),
    sample_csv: csv
  };
}

function historyRecord(value: Backend.ImportView): ImportHistoryRecord {
  return {
    id: value.id,
    kind: value.kind,
    filename: value.original_filename,
    status: value.status,
    total_rows: value.total_rows,
    imported_rows: value.imported_rows,
    error_rows: value.invalid_rows,
    created_at: value.created_at,
    completed_at: value.completed_at
  };
}

function terminalValidation(value: Backend.ImportView): boolean {
  return [
    "ready",
    "validation_failed",
    "import_failed",
    "cancelled",
    "expired"
  ].includes(value.status);
}

function terminalCommit(value: Backend.ImportView): boolean {
  return ["completed", "import_failed", "cancelled", "expired"].includes(
    value.status
  );
}

export function createLiveImportsApi(
  client: ApiHttpClient
): InsightForgeApi["imports"] {
  return {
    async templates(signal) {
      return Promise.all(
        importKinds.map(async (kind) => {
          const artifact = await client.download(`/imports/templates/${kind}`, {
            signal
          });
          return templateFromCsv(kind, await artifact.blob.text());
        })
      );
    },
    async history(organizationId, signal) {
      const envelope = await client.collection<Backend.ImportView>("/imports", {
        organizationId,
        query: { page: 1, page_size: 100 },
        signal
      });
      return envelope.data.map(historyRecord);
    },
    async validate(organizationId, input, signal) {
      const file = new Blob([input.content], {
        type: input.mime_type || "text/csv"
      });
      const digest = await sha256Hex(file);
      const form = new FormData();
      form.append("kind", input.kind);
      form.append("file", file, input.filename);
      const uploaded = await client.request<Backend.ImportView>("/imports", {
        method: "POST",
        organizationId,
        idempotent: true,
        body: form,
        headers: { "X-Content-SHA256": digest },
        signal
      });
      const dataImport = await pollUntil(
        async (pollSignal) =>
          (
            await client.request<Backend.ImportView>(
              `/imports/${uploaded.data.id}`,
              { organizationId, signal: pollSignal }
            )
          ).data,
        {
          signal,
          isComplete: terminalValidation,
          isFailed: (value) =>
            ["import_failed", "cancelled", "expired"].includes(value.status)
        }
      );
      const [preview, errors] = await Promise.all([
        client.request<Backend.ImportPreviewView>(
          `/imports/${dataImport.id}/preview`,
          { organizationId, signal }
        ),
        client.collection<Backend.ImportErrorView>(
          `/imports/${dataImport.id}/errors`,
          {
            organizationId,
            query: { page: 1, page_size: 25 },
            signal
          }
        )
      ]);
      return {
        import_id: dataImport.id,
        kind: dataImport.kind,
        filename: dataImport.original_filename,
        status: dataImport.status === "ready" ? "ready" : "validation_failed",
        headers: preview.data.headers,
        preview_rows: preview.data.rows.map((row) =>
          Object.fromEntries(
            Object.entries(row).map(([key, value]) => [
              key,
              String(value ?? "")
            ])
          )
        ),
        total_rows: dataImport.total_rows,
        valid_rows: dataImport.valid_rows,
        error_rows: dataImport.invalid_rows,
        errors: errors.data,
        errors_truncated: errors.meta.pagination.has_next,
        duplicate_policy: "create_only"
      } satisfies ImportPreview;
    },
    async commit(organizationId, importId, signal) {
      const current = await client.request<Backend.ImportView>(
        `/imports/${importId}`,
        { organizationId, signal }
      );
      const committed = await client.request<Backend.ImportView>(
        `/imports/${importId}/commit`,
        {
          method: "POST",
          organizationId,
          idempotent: true,
          json: {
            content_sha256: current.data.content_sha256,
            duplicate_policy: "create_only"
          },
          signal
        }
      );
      const completed = await pollUntil(
        async (pollSignal) =>
          (
            await client.request<Backend.ImportView>(`/imports/${importId}`, {
              organizationId,
              signal: pollSignal
            })
          ).data,
        {
          signal,
          isComplete: terminalCommit,
          isFailed: (value) =>
            ["import_failed", "cancelled", "expired"].includes(value.status)
        }
      );
      return historyRecord(
        completed.status === "importing" ? committed.data : completed
      );
    }
  };
}
