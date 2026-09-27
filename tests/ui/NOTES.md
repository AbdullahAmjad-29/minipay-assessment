# UI test notes

Run: `python3 -m pytest tests/ui/ --base-url http://127.0.0.1:8000 --tracing on --screenshot on --video on --html=tests/ui/report.html --self-contained-html -v`

Evidence: screenshots, video, and Playwright trace.zip per test land in test-results/ (gitignored, regenerated each run); report.html is a full HTML report of the last run.

No login journey: this app has no per-user UI auth (only the API's service-level X-API-Key), documented as a deliberate scope decision.

CI integration: run this suite headless in CI on every PR/merge to main, same as the API suite - it's fast (~25s) and covers the core money-moving path (create + search), so it belongs in the fast/every-release gate, not a separate regression pass. A larger regression suite (more edge cases, multiple browsers, visual regression) would run on a schedule or pre-release instead, since that's slower and less critical to block every merge on.
EOF
