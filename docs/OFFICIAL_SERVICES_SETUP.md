# AYEC official services

- Public website: https://www.ayecpro.com
- Application: https://panel.ayecpro.com
- Platform sender: info@ayecpro.com
- Registration, license and payment notifications: destek@ayecpro.com
- Reply-To: destek@ayecpro.com

Run CONFIGURE_AYEC_OFFICIAL_SERVICES.cmd as administrator on the application
server after installing the update. Enter the SMTP hostname and port displayed
by Turhost, and the info mailbox password. The tool verifies TLS and SMTP
authentication before saving. It sends no test message. A successful SMTP
login does not prove inbox delivery; verify a registration and license message
after configuration and check the mailbox spam folder if needed.

Settings are stored outside the public web directory in official-services.json.
Only Windows administrators and SYSTEM can read this file. The application task
must run as one of these identities. Do not upload this file or include it in
releases. Application updates preserve it. No customer desktop installer needs
the official mailbox password. Desktop provisioning and license requests send
platform mail on the server; tenant-owned service mail retains tenant SMTP.

Optional environment overrides: AYEC_OFFICIAL_SMTP_HOST,
AYEC_OFFICIAL_SMTP_PORT, AYEC_OFFICIAL_SMTP_PASSWORD, AYEC_GOOGLE_CLIENT_ID.
AYEC_OFFICIAL_CONFIG can select another server-only configuration file.

Google: create or reuse a Web application OAuth Client ID and authorize
https://panel.ayecpro.com as a JavaScript origin. The value ends with
.apps.googleusercontent.com. Gemini API keys do not work for sign-in.
The GIS popup flow needs no client secret or redirect URI. Complete Google
consent-screen branding, support contact, authorized domain, privacy policy,
and production publishing as required by Google Cloud.

The Google button appears only when a Client ID is configured. Registration
requires company, sector and username. Server-side token
verification binds the Google subject to the newly created account. Existing
password accounts are not automatically linked by email. Disabled accounts and
expired licenses remain blocked on Google login.

The existing platform owner identity is preserved separately from public email.
Changing public contact addresses does not change existing login credentials.

References:
https://developers.google.com/identity/gsi/web/guides/verify-google-id-token
https://developers.google.com/identity/gsi/web/reference/js-reference
