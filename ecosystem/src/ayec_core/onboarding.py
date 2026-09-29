"""Shared first-run product registration contract."""

REQUIRED_PROFILE_FIELDS = ("company_name", "requester_name", "requester_phone", "requester_email", "company_address")


def profile_complete(profile):
    values = profile or {}
    return all(str(values.get(field) or "").strip() for field in REQUIRED_PROFILE_FIELDS)


def save_product_profile(runtime, *, company_name, requester_name, requester_phone,
                         requester_email, company_address):
    runtime.set_profile(email=requester_email, company=company_name,
                        contact=requester_name, phone=requester_phone)
    runtime.identity.setdefault("profile", {})["company_address"] = str(company_address or "").strip()
    runtime.identity_store.save(runtime.identity)
