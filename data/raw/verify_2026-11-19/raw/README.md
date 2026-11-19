# Raw text of the official pages read on 2026-11-19

Each `.md` file here is the **unmodified text returned by the retrieval channel** (the agent's
page-fetch tool) for the URL named in its first line, at the time named in its `retrieved`
line. It is committed so that every row parsed out of it by
`tools/session-164d832b-capture.py` can be re-derived and checked by hand against the live
page.

**Transport fact, measured, not assumed.** Direct HTTPS from the build sandbox to
`www.nba.com`, `official.nba.com` and `cdn.nba.com` fails inside the TLS handshake
(`curl: (35) OpenSSL SSL_ERROR_SYSCALL`, HTTP code `000`, 2026-11-19T12:16Z). The pages
below were therefore read through the agent's page-fetch channel, which does reach those
hosts. Nothing here is remembered from a previous session or from model knowledge.

**Do not edit these files by hand.** If a page is re-read, a new dated file is added; these
are retrieval artefacts.
