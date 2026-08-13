from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

from insightforge.models.enums import OrganizationRole


class Permission(StrEnum):
    VIEW_BUSINESS_DATA = "view_business_data"
    ASK_ANALYTICS = "ask_analytics"
    GENERATE_REPORTS = "generate_reports"
    EXPORT_REPORTS = "export_reports"
    MANAGE_BUSINESS_DATA = "manage_business_data"
    IMPORT_DATA = "import_data"
    VIEW_TEAM = "view_team"
    INVITE_MEMBERS = "invite_members"
    CHANGE_ROLES = "change_roles"
    EDIT_ORGANIZATION = "edit_organization"
    VIEW_AUDIT_LOG = "view_audit_log"
    MANAGE_BILLING = "manage_billing"
    TRANSFER_OWNERSHIP = "transfer_ownership"
    DELETE_ORGANIZATION = "delete_organization"
    CHANGE_CREDENTIALS = "change_credentials"


MEMBER_PERMISSIONS = frozenset(
    {
        Permission.VIEW_BUSINESS_DATA,
        Permission.ASK_ANALYTICS,
        Permission.GENERATE_REPORTS,
        Permission.EXPORT_REPORTS,
        Permission.VIEW_TEAM,
        Permission.CHANGE_CREDENTIALS,
    }
)
ADMIN_PERMISSIONS = MEMBER_PERMISSIONS | {
    Permission.MANAGE_BUSINESS_DATA,
    Permission.IMPORT_DATA,
    Permission.INVITE_MEMBERS,
    Permission.EDIT_ORGANIZATION,
    Permission.VIEW_AUDIT_LOG,
}
OWNER_PERMISSIONS = ADMIN_PERMISSIONS | {
    Permission.CHANGE_ROLES,
    Permission.MANAGE_BILLING,
    Permission.TRANSFER_OWNERSHIP,
    Permission.DELETE_ORGANIZATION,
}

ROLE_PERMISSIONS: dict[str, frozenset[Permission]] = {
    OrganizationRole.MEMBER.value: MEMBER_PERMISSIONS,
    OrganizationRole.ADMIN.value: frozenset(ADMIN_PERMISSIONS),
    OrganizationRole.OWNER.value: frozenset(OWNER_PERMISSIONS),
}

DEMO_DENIED_PERMISSIONS = frozenset(
    {
        Permission.INVITE_MEMBERS,
        Permission.CHANGE_ROLES,
        Permission.TRANSFER_OWNERSHIP,
        Permission.DELETE_ORGANIZATION,
        Permission.CHANGE_CREDENTIALS,
    }
)


@dataclass(frozen=True, slots=True)
class PermissionSet:
    role: str
    values: frozenset[Permission]
    is_demo: bool

    def allows(self, permission: Permission) -> bool:
        return permission in self.values


def permissions_for(role: str, *, is_demo: bool = False) -> PermissionSet:
    values = ROLE_PERMISSIONS.get(role, frozenset())
    if is_demo:
        values = values - DEMO_DENIED_PERMISSIONS
    return PermissionSet(role=role, values=values, is_demo=is_demo)
