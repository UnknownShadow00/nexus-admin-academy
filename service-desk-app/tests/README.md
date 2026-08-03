# tests

Cross-app Playwright E2E specs and shared fixtures.

`e2e/remote-desktop-workflows.spec.ts` covers the VPN, DNS, and Print Spooler
ticket workflows through the browser. Run them after a production build with:

```sh
pnpm test:e2e
```
