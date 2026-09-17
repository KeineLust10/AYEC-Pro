# AYEC Pro Ecosystem Development Rules

Every new AYEC Pro desktop or web product must join the shared platform before it is considered complete.

The AYEC Pro Technical Service application is a product. `Admin_Konsol` is the management center. `Web_Arayuzu` owns the central API, tenant registry, license catalog, backup registry, restore commands, and audit trail.

Before implementation starts, each product must declare:

- a unique `product_code`
- a public product name
- a local SQLite database name
- a server backup folder name
- its license catalog and trial policy
- tenant and device identity rules
- backup, restore, and synchronization support
- smart import capabilities
- its Admin_Konsol filter and API routes

Products must not create independent license, authentication, backup, restore, or pricing systems. They must use the AYEC Core contract and connect to `Web_Arayuzu` and `Admin_Konsol`.

Any developer or coding agent adding a product must first report the product contract, required central API changes, Admin_Konsol changes, migrations, and verification plan. If the shared integration is missing, the developer or agent must notify the owner and implement it as part of the product work.

License prices are owned by the central catalog. Desktop fallback prices may be used only for offline display and must be generated from the approved catalog. Market research informs the catalog review; clients must never silently invent or override prices.

Each backup must be associated with `product_code`, `tenant_id`, `hardware_id`, checksum, size, creation time, and source. Restore must validate SQLite integrity and preserve the current local database before replacement.

Smart import must use preview and explicit confirmation before writing business data. Invalid rows must be reported and must not partially mutate production tables.

