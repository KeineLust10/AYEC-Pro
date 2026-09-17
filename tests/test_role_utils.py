from src.utils.role_utils import is_admin_role, normalize_role, role_key


def test_all_desktop_owner_role_labels_have_admin_access():
    roles = (
        "Admin",
        "Administrator",
        "Super Admin",
        "Super Administrator",
        "Master Admin",
        "Platform Admin",
        "Company Admin",
        "Master",
        "Y\u00f6netici",
        "Sistem Y\u00f6neticisi",
        "Firma Y\u00f6neticisi",
        "Firma Sahibi",
        "En Yetkili Ki\u015fi",
        "Owner",
    )

    for role in roles:
        assert is_admin_role(role), role
        assert normalize_role(role) in {"Admin", "Master"}


def test_regular_desktop_roles_do_not_gain_admin_access():
    for role in ("Manager", "Teknisyen", "Muhasebe", "Personel", "User"):
        assert not is_admin_role(role), role


def test_role_key_is_case_space_and_turkish_character_safe():
    assert role_key("  EN YETK\u0130L\u0130 K\u0130\u015e\u0130  ") == "en yetkili kisi"
    assert role_key("Firma-Y\u00f6neticisi") == "firma yoneticisi"
