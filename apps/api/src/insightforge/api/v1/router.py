from fastapi import APIRouter

from insightforge.api.v1 import (
    analytics,
    auth,
    billing,
    customers,
    imports,
    intelligence,
    orders,
    organizations,
    products,
    reports,
    team,
    users,
)

router = APIRouter()
router.include_router(auth.router)
router.include_router(organizations.router)
router.include_router(users.router)
router.include_router(customers.router)
router.include_router(products.router)
router.include_router(orders.router)
router.include_router(analytics.router)
router.include_router(intelligence.router)
router.include_router(reports.router)
router.include_router(imports.router)
router.include_router(team.router)
router.include_router(billing.router)
