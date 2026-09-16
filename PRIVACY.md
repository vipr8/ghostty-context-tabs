# Privacy

## Installed software

Ghostty Context Tabs runs locally. The installed software does not contain
analytics, telemetry, advertising, crash reporting, update checks or any other
network client.

The allocator writes `~/.local/state/ghostty-context-tabs/terminal-tabs.json`.
That file contains a random tab identifier, color information, a local process
identifier and a TTY name. Its directory is private to the current user and the
file is written with mode `0600`.

Repository, task, tool and state labels are held by the current terminal and,
when enabled, the local tmux server. They are intentionally visible in terminal
titles and context bars. They can therefore appear in screenshots, recordings,
window-switcher previews or screen-sharing sessions. Do not use sensitive text
as a label.

## Hosted guide

The guide at [labs.avisekdas.com](https://labs.avisekdas.com/) uses Cloudflare
Web Analytics to count page visits, record the referring page and measure page
performance. This analytics beacon is part of the website only. It is not
included in the Context Tabs software and is not installed by the setup steps.

Cloudflare states that its beacon does not use cookies, local storage, session
storage or IndexedDB; it does not track individual visitors across Cloudflare
customers; and it discards the source IP address rather than storing it in its
core databases or logs. See Cloudflare's [RUM beacon privacy
information](https://developers.cloudflare.com/speed/observatory/rum-beacon/)
and [data collection
documentation](https://developers.cloudflare.com/web-analytics/data-metrics/data-origin-and-collection/).
