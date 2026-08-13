from __future__ import annotations

from insightforge.core.policies import Permission, permissions_for


def test_role_permissions_follow_the_baseline_matrix() -> None:
    member = permissions_for("member")
    admin = permissions_for("admin")
    owner = permissions_for("owner")

    assert member.allows(Permission.VIEW_BUSINESS_DATA)
    assert not member.allows(Permission.MANAGE_BUSINESS_DATA)
    assert admin.allows(Permission.MANAGE_BUSINESS_DATA)
    assert admin.allows(Permission.INVITE_MEMBERS)
    assert not admin.allows(Permission.CHANGE_ROLES)
    assert owner.allows(Permission.CHANGE_ROLES)
    assert owner.allows(Permission.MANAGE_BILLING)


def test_demo_owner_loses_sensitive_external_effects() -> None:
    demo_owner = permissions_for("owner", is_demo=True)

    assert demo_owner.allows(Permission.MANAGE_BUSINESS_DATA)
    assert demo_owner.allows(Permission.GENERATE_REPORTS)
    assert demo_owner.allows(Permission.MANAGE_BILLING)
    assert not demo_owner.allows(Permission.INVITE_MEMBERS)
    assert not demo_owner.allows(Permission.TRANSFER_OWNERSHIP)
    assert not demo_owner.allows(Permission.DELETE_ORGANIZATION)
    assert not demo_owner.allows(Permission.CHANGE_CREDENTIALS)
