# AYEC Pro public service tracking

The PDF service QR code now contains a signed URL:

`https://ayecpro.com/servis/takip/<token>`

Set the same secret on the desktop application and the web server before
printing production receipts:

```text
AYEC_TRACKING_SECRET=<long-random-secret>
AYEC_SERVICE_TRACKING_URL=https://ayecpro.com/servis/takip
```

The web server accepts both of these public routes:

* `GET /servis/takip/<token>` returns the mobile tracking page.
* `GET /api/public/service/<token>` returns the safe JSON summary.

The public response contains tracking number, device, status, received date,
and delivery type. Customer name, phone, fault details, parts, and prices are
not exposed. Each successful lookup is recorded in the tenant database in the
`service_tracking_access` table with time, IP address, and user agent.

For Turhost deployment, run the AYEC web server behind HTTPS and proxy the
`ayecpro.com` virtual host to that server. The DNS A record must point to the
server public IP and the SSL certificate must cover `ayecpro.com`. Keep the
tracking secret out of source control and configure it in the process
environment on both sides.
