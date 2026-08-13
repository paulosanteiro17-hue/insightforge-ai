import type * as Backend from "@/lib/api/backend-contracts";
import {
  type CustomerListQuery,
  type InsightForgeApi,
  type OrderListQuery,
  type ProductListQuery
} from "@/lib/api/contracts";
import { ApiHttpClient } from "@/lib/api/http-client";
import {
  loadCurrentWeeklySummary,
  regenerateWeeklySummary
} from "@/lib/api/live-intelligence-adapter";
import {
  mapAnalyticsPerformance,
  mapCustomer,
  mapCustomerDetail,
  mapDashboard,
  mapOrder,
  mapOrderDetail,
  mapOrganization,
  mapPagination,
  mapProduct,
  mapProductDetail,
  mapSession
} from "@/lib/api/live-mappers";
import { rangeDates } from "@/lib/api/live-ranges";

type CoreApi = Pick<
  InsightForgeApi,
  "auth" | "organizations" | "analytics" | "orders" | "customers" | "products"
>;

function etagOrVersion(etag: string | null, version: number): string {
  return etag ?? `"${version}"`;
}

const orderSort: Record<OrderListQuery["sort"], string> = {
  ordered_at_desc: "-ordered_at",
  ordered_at_asc: "ordered_at",
  total_desc: "-total",
  total_asc: "total"
};

const customerSort: Record<CustomerListQuery["sort"], string> = {
  total_spent_desc: "-total_spent",
  total_spent_asc: "total_spent",
  name_asc: "name",
  last_order_desc: "-last_order_at"
};

const productSort: Record<ProductListQuery["sort"], string> = {
  revenue_desc: "-revenue",
  revenue_asc: "revenue",
  units_desc: "-units_sold",
  name_asc: "name",
  price_desc: "-average_price"
};

export function createLiveCoreApi(client: ApiHttpClient): CoreApi {
  const orders: CoreApi["orders"] = {
    async list(organizationId, query, signal) {
      const envelope = await client.collection<Backend.OrderView>("/orders", {
        organizationId,
        query: {
          page: query.page,
          page_size: query.page_size,
          q: query.search,
          status: query.status,
          sort: orderSort[query.sort],
          ...rangeDates(query.range)
        },
        signal
      });
      const paginated = mapPagination(envelope);
      return { ...paginated, items: paginated.items.map(mapOrder) };
    },
    async getById(organizationId, orderId, signal) {
      const response = await client.request<Backend.OrderView>(
        `/orders/${orderId}`,
        {
          organizationId,
          signal
        }
      );
      return mapOrderDetail(
        response.data,
        etagOrVersion(response.etag, response.data.version)
      );
    },
    async updateStatus(organizationId, orderId, status, ifMatch, signal) {
      const response = await client.request<Backend.OrderView>(
        `/orders/${orderId}`,
        {
          method: "PATCH",
          organizationId,
          ifMatch,
          json: { status },
          signal
        }
      );
      return mapOrderDetail(
        response.data,
        etagOrVersion(response.etag, response.data.version)
      );
    },
    async cancel(organizationId, orderId, reason, signal) {
      const response = await client.request<Backend.OrderView>(
        `/orders/${orderId}/cancel`,
        {
          method: "POST",
          organizationId,
          idempotent: true,
          json: { reason },
          signal
        }
      );
      return mapOrderDetail(
        response.data,
        etagOrVersion(response.etag, response.data.version)
      );
    },
    async refund(organizationId, orderId, reason, signal) {
      const response = await client.request<Backend.OrderView>(
        `/orders/${orderId}/refund`,
        {
          method: "POST",
          organizationId,
          idempotent: true,
          json: { reason },
          signal
        }
      );
      return mapOrderDetail(
        response.data,
        etagOrVersion(response.etag, response.data.version)
      );
    }
  };

  return {
    auth: {
      async signIn(input, signal) {
        const response = await client.request<Backend.SessionView>(
          "/auth/login",
          {
            method: "POST",
            json: input,
            signal
          }
        );
        return mapSession(response.data);
      },
      async signUp(input, signal) {
        const response = await client.request<Backend.SessionView>(
          "/auth/register",
          {
            method: "POST",
            json: input,
            signal
          }
        );
        return mapSession(response.data);
      },
      async createDemoSession(signal) {
        const response = await client.request<Backend.SessionView>(
          "/auth/demo-session",
          {
            method: "POST",
            idempotent: true,
            json: {},
            signal
          }
        );
        return mapSession(response.data);
      },
      async requestPasswordReset(email, signal) {
        const response = await client.request<Backend.PasswordResetRequestView>(
          "/auth/password-reset-requests",
          { method: "POST", json: { email }, signal }
        );
        return response.data;
      },
      async confirmPasswordReset(token, password, signal) {
        await client.request<void>("/auth/password-resets", {
          method: "POST",
          json: { token, password },
          signal
        });
      },
      async signOut(signal) {
        await client.request<void>("/auth/logout", { method: "POST", signal });
        client.clearCsrfToken();
      }
    },
    organizations: {
      async list(signal) {
        const response = await client.request<
          Backend.OrganizationSummaryView[]
        >("/organizations", { signal });
        return response.data.map(mapOrganization);
      },
      async getBySlug(slug, signal) {
        const response = await client.request<
          Backend.OrganizationSummaryView[]
        >("/organizations", { signal });
        const organization = response.data.find((item) => item.slug === slug);
        return organization ? mapOrganization(organization) : null;
      },
      async create(input, signal) {
        const response = await client.request<Backend.OrganizationSummaryView>(
          "/organizations",
          { method: "POST", json: input, signal }
        );
        return mapOrganization(response.data);
      }
    },
    analytics: {
      async getOverview(organizationId, range, signal) {
        const [response, weeklySummary] = await Promise.all([
          client.request<Backend.AnalyticsView>("/analytics/overview", {
            organizationId,
            query: { range },
            signal
          }),
          loadCurrentWeeklySummary(client, organizationId, signal)
        ]);
        return {
          ...mapDashboard(organizationId, range, response.data),
          weekly_summary: weeklySummary
        };
      },
      async getPerformance(organizationId, range, signal) {
        const response = await client.request<Backend.AnalyticsView>(
          "/analytics/overview",
          { organizationId, query: { range }, signal }
        );
        return mapAnalyticsPerformance(organizationId, range, response.data);
      },
      regenerateWeeklySummary(organizationId, signal) {
        return regenerateWeeklySummary(client, organizationId, signal);
      }
    },
    orders,
    customers: {
      async list(organizationId, query, signal) {
        const envelope = await client.collection<Backend.CustomerView>(
          "/customers",
          {
            organizationId,
            query: {
              page: query.page,
              page_size: query.page_size,
              q: query.search,
              status: query.status,
              segment: query.segment,
              sort: customerSort[query.sort]
            },
            signal
          }
        );
        const paginated = mapPagination(envelope);
        return { ...paginated, items: paginated.items.map(mapCustomer) };
      },
      async getById(organizationId, customerId, signal) {
        const [customer, metrics, customerOrders] = await Promise.all([
          client.request<Backend.CustomerView>(`/customers/${customerId}`, {
            organizationId,
            signal
          }),
          client.request<Backend.CustomerMetricsView>(
            `/customers/${customerId}/metrics`,
            { organizationId, signal }
          ),
          client.collection<Backend.OrderView>(
            `/customers/${customerId}/orders`,
            {
              organizationId,
              query: { page: 1, page_size: 10, sort: "-ordered_at" },
              signal
            }
          )
        ]);
        return mapCustomerDetail(
          customer.data,
          metrics.data,
          customerOrders,
          etagOrVersion(customer.etag, customer.data.version)
        );
      },
      async create(organizationId, input, signal) {
        const response = await client.request<Backend.CustomerView>(
          "/customers",
          {
            method: "POST",
            organizationId,
            json: input,
            signal
          }
        );
        return mapCustomer(response.data);
      },
      async update(organizationId, customerId, input, ifMatch, signal) {
        const response = await client.request<Backend.CustomerView>(
          `/customers/${customerId}`,
          {
            method: "PATCH",
            organizationId,
            ifMatch,
            json: input,
            signal
          }
        );
        return mapCustomer(response.data);
      },
      async archive(organizationId, customerId, ifMatch, signal) {
        await client.request<void>(`/customers/${customerId}`, {
          method: "DELETE",
          organizationId,
          ifMatch,
          signal
        });
      }
    },
    products: {
      async list(organizationId, query, signal) {
        const envelope = await client.collection<Backend.ProductView>(
          "/products",
          {
            organizationId,
            query: {
              page: query.page,
              page_size: query.page_size,
              q: query.search,
              status: query.status,
              category: query.category,
              sort: productSort[query.sort]
            },
            signal
          }
        );
        const paginated = mapPagination(envelope);
        return { ...paginated, items: paginated.items.map(mapProduct) };
      },
      async getById(organizationId, productId, range, signal) {
        const [product, metrics] = await Promise.all([
          client.request<Backend.ProductView>(`/products/${productId}`, {
            organizationId,
            signal
          }),
          client.request<Backend.ProductMetricsView>(
            `/products/${productId}/metrics`,
            {
              organizationId,
              query: { range },
              signal
            }
          )
        ]);
        return mapProductDetail(
          product.data,
          metrics.data,
          range,
          etagOrVersion(product.etag, product.data.version)
        );
      },
      async create(organizationId, input, signal) {
        const response = await client.request<Backend.ProductView>(
          "/products",
          {
            method: "POST",
            organizationId,
            json: input,
            signal
          }
        );
        return mapProduct(response.data);
      },
      async update(organizationId, productId, input, ifMatch, signal) {
        const response = await client.request<Backend.ProductView>(
          `/products/${productId}`,
          {
            method: "PATCH",
            organizationId,
            ifMatch,
            json: input,
            signal
          }
        );
        return mapProduct(response.data);
      },
      async archive(organizationId, productId, ifMatch, signal) {
        await client.request<void>(`/products/${productId}`, {
          method: "DELETE",
          organizationId,
          ifMatch,
          signal
        });
      }
    }
  };
}
