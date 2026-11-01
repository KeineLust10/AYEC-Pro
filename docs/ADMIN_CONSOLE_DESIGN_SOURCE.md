# Admin Management Console Design Source

The single source of truth is the absolute Windows directory `C:\Users\yedek\Desktop\Y\u00f6netim Konsolu Tasar\u0131m\`. Decode each `\uNNNN` sequence as its Unicode character.

Each screen reference is the matching `.html` and `.md` pair. The mapping is enforced by `tools/quality/admin_web_offscreen_capture.py` through the `single_source_reference` capture check.

This reference set applies to the Admin Management Console (`Admin_Konsol` and the web control center) only. Do not apply it to the AYEC Pro Technical Service product dashboard.

Keep the unified application Side Menu and shared shell navigation unchanged. Match all other screen content to the reference pair.

Use offscreen desktop and mobile captures for visual inspection. Capture pages with UTF-8 and system fallback fonts `Segoe UI` and `Arial`.
