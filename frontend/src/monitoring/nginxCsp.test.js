import { readFileSync } from "node:fs";
import { resolve } from "node:path";
import { describe, expect, it } from "vitest";

const SENTRY_INGEST_ORIGIN = "https://o4511978744840192.ingest.us.sentry.io";
const configPath = resolve(process.cwd(), "nginx.host.conf");
const config = readFileSync(configPath, "utf8");

function parsePolicies(source) {
  return [...source.matchAll(/add_header\s+Content-Security-Policy\s+"([^"]+)"\s+always;/g)].map(
    ([, policy]) => Object.fromEntries(
      policy.split(";").map((directive) => directive.trim()).filter(Boolean).map((directive) => {
        const [name, ...values] = directive.split(/\s+/);
        return [name, values];
      }),
    ),
  );
}

const policies = parsePolicies(config);
const nexusPolicies = policies.filter((policy) => policy["frame-src"]?.includes("https://www.youtube.com"));

describe("production nginx CSP", () => {
  it("allows only the exact Sentry ingestion origin from Nexus documents", () => {
    expect(nexusPolicies).toHaveLength(2);
    for (const policy of nexusPolicies) {
      expect(policy["connect-src"]).toEqual(["'self'", SENTRY_INGEST_ORIGIN]);
    }

    const allSources = policies.flatMap((policy) => Object.values(policy).flat());
    expect(allSources).not.toContain("https:");
    expect(allSources).not.toContain("*.sentry.io");
    expect(allSources).not.toContain("*.ingest.sentry.io");
    expect(allSources.filter((source) => source === SENTRY_INGEST_ORIGIN)).toHaveLength(2);
  });

  it("permits Replay's blob compression worker without broadening scripts", () => {
    for (const policy of nexusPolicies) {
      expect(policy["worker-src"]).toEqual(["'self'", "blob:"]);
      expect(policy["script-src"]).toEqual(["'self'"]);
      expect(policy["script-src"]).not.toContain("blob:");
      expect(policy["script-src"]).not.toContain("'unsafe-eval'");
      expect(policy["child-src"]).toBeUndefined();
    }
  });

  it("retains the restrictive Nexus security directives", () => {
    for (const policy of nexusPolicies) {
      expect(policy["default-src"]).toEqual(["'self'"]);
      expect(policy["object-src"]).toEqual(["'none'"]);
      expect(policy["frame-ancestors"]).toEqual(["'self'"]);
      expect(policy["base-uri"]).toEqual(["'self'"]);
      expect(policy["form-action"]).toEqual(["'self'"]);
      expect(policy["frame-src"]).toEqual([
        "https://www.youtube.com",
        "https://www.youtube-nocookie.com",
      ]);
    }
  });
});
