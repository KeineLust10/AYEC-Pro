# AYEC Core shared contract

`ayec_core` is the common product contract for AYEC Pro desktop applications.
It reads `../ecosystem/products.json` and provides one identity and storage
layout for licensing, database backup, restore, and smart import integrations.

Applications must declare a catalog `product_code` and use `ProductContract`
instead of inventing product names or backup paths locally.
