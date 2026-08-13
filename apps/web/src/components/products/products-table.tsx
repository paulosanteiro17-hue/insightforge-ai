import Link from "next/link";
import { ExternalLink } from "lucide-react";
import { PaginationControls } from "@/components/data/pagination-controls";
import { StatusBadge } from "@/components/data/status-badge";
import { Card } from "@/components/ui/card";
import type { PaginationMeta, ProductListItem } from "@/lib/api/contracts";
import { formatMoney } from "@/lib/format";

export function ProductsTable({
  products,
  pagination,
  organizationSlug
}: {
  products: ProductListItem[];
  pagination: PaginationMeta;
  organizationSlug: string;
}) {
  return (
    <Card className="overflow-hidden">
      <div className="hidden overflow-x-auto md:block">
        <table className="w-full text-left text-sm">
          <caption className="sr-only">
            Products matching the selected filters
          </caption>
          <thead className="bg-ink-50/80 text-ink-500 text-[10px] font-bold tracking-[0.11em] uppercase">
            <tr>
              <th className="px-5 py-3.5">Product</th>
              <th className="px-5 py-3.5">Status</th>
              <th className="px-5 py-3.5 text-right">Price</th>
              <th className="px-5 py-3.5 text-right">Units sold</th>
              <th className="px-5 py-3.5 text-right">Revenue</th>
              <th className="px-5 py-3.5 text-right">Average price</th>
              <th className="w-14">
                <span className="sr-only">Open</span>
              </th>
            </tr>
          </thead>
          <tbody className="divide-ink-100 divide-y">
            {products.map((product) => (
              <tr
                key={product.id}
                className="hover:bg-ink-50/60 transition-colors"
              >
                <td className="px-5 py-4">
                  <Link
                    href={`/app/${organizationSlug}/products/${product.id}`}
                    className="text-ink-950 font-semibold hover:text-teal-700"
                  >
                    {product.name}
                  </Link>
                  <p className="text-ink-400 mt-0.5 font-mono text-[10px]">
                    {product.sku} · {product.category}
                  </p>
                </td>
                <td className="px-5 py-4">
                  <StatusBadge status={product.status} />
                </td>
                <td className="text-ink-600 px-5 py-4 text-right">
                  {formatMoney(product.unit_price_minor)}
                </td>
                <td className="text-ink-700 px-5 py-4 text-right font-medium">
                  {product.units_sold}
                </td>
                <td className="text-ink-950 px-5 py-4 text-right font-bold">
                  {formatMoney(product.revenue_minor)}
                </td>
                <td className="text-ink-700 px-5 py-4 text-right text-xs font-semibold">
                  {product.average_price_minor === null
                    ? "Not available"
                    : formatMoney(product.average_price_minor)}
                </td>
                <td className="pr-4">
                  <Link
                    href={`/app/${organizationSlug}/products/${product.id}`}
                    aria-label={`View ${product.name}`}
                    className="text-ink-400 hover:bg-ink-100 hover:text-ink-900 grid size-9 place-items-center rounded-lg"
                  >
                    <ExternalLink className="size-4" aria-hidden="true" />
                  </Link>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <div className="divide-ink-100 divide-y md:hidden">
        {products.map((product) => (
          <article key={product.id} className="p-4">
            <div className="flex items-start justify-between gap-3">
              <div className="min-w-0">
                <Link
                  href={`/app/${organizationSlug}/products/${product.id}`}
                  className="text-ink-950 block truncate text-sm font-bold"
                >
                  {product.name}
                </Link>
                <p className="text-ink-400 mt-1 font-mono text-[10px]">
                  {product.sku} · {product.category}
                </p>
              </div>
              <StatusBadge status={product.status} />
            </div>
            <dl className="bg-ink-50 mt-4 grid grid-cols-3 gap-2 rounded-xl p-3 text-center">
              <div>
                <dt className="text-ink-400 text-[9px] uppercase">Revenue</dt>
                <dd className="text-ink-900 mt-1 text-xs font-bold">
                  {formatMoney(product.revenue_minor)}
                </dd>
              </div>
              <div>
                <dt className="text-ink-400 text-[9px] uppercase">Units</dt>
                <dd className="text-ink-900 mt-1 text-xs font-bold">
                  {product.units_sold}
                </dd>
              </div>
              <div>
                <dt className="text-ink-400 text-[9px] uppercase">Avg price</dt>
                <dd className="text-ink-900 mt-1 text-xs font-bold">
                  {product.average_price_minor === null
                    ? "N/A"
                    : formatMoney(product.average_price_minor)}
                </dd>
              </div>
            </dl>
          </article>
        ))}
      </div>
      <PaginationControls
        page={pagination.page}
        totalPages={pagination.total_pages}
        totalItems={pagination.total_items}
        itemLabel="products"
      />
    </Card>
  );
}
