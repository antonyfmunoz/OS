import { describe, it, expect } from "vitest";
import {
  generateAnalyticsInjections,
  buildProviderCode,
  buildIdentifyCode,
} from "../../../lib/analytics-delivery/analytics-injector.js";

// ─── Fixtures ─────────────────────────────────────────────────────────────────

const pageWithLoadAndClick = {
  name: "Dashboard",
  filePath: "client/src/pages/dashboard.tsx",
  events: [
    { name: "page viewed", trigger: "load", properties: ["user_id"] },
    { name: "button clicked", trigger: "click", properties: ["button_label"] },
  ],
};

const pageWithLoadOnly = {
  name: "Settings",
  filePath: "client/src/pages/settings.tsx",
  events: [
    { name: "Settings Viewed", trigger: "page_view", properties: [] },
  ],
};

const pageWithNoEvents = {
  name: "Empty",
  filePath: "client/src/pages/empty.tsx",
  events: [],
};

const pageWithSubmit = {
  name: "Login",
  filePath: "client/src/pages/login.tsx",
  events: [
    { name: "form submitted", trigger: "submit", properties: ["email"] },
    { name: "login page loaded", trigger: "mount", properties: [] },
  ],
};

// ─── Tests ────────────────────────────────────────────────────────────────────

describe("generateAnalyticsInjections", () => {
  it("Test 1: returns array with 1 AnalyticsInjection with importCode containing posthog-js/react import", () => {
    const injections = generateAnalyticsInjections([pageWithLoadAndClick]);
    expect(injections).toHaveLength(1);
    expect(injections[0].importCode).toContain('import { usePostHog } from "posthog-js/react"');
  });

  it("Test 2: hookCode contains usePostHog() call", () => {
    const injections = generateAnalyticsInjections([pageWithLoadAndClick]);
    expect(injections[0].hookCode).toContain("const posthog = usePostHog();");
  });

  it("Test 3: captureCode for load event contains snake_case normalized event name", () => {
    const injections = generateAnalyticsInjections([pageWithLoadAndClick]);
    // "page viewed" -> "page_viewed"
    expect(injections[0].captureCode).toContain('posthog?.capture("page_viewed"');
  });

  it("Test 4: captureCode wraps load event in useEffect with useRef dedupe guard for React 18 Strict Mode", () => {
    const injections = generateAnalyticsInjections([pageWithLoadAndClick]);
    const code = injections[0].captureCode;
    expect(code).toContain("useRef(false)");
    expect(code).toContain("hasFired.current");
    expect(code).toContain("useEffect");
  });

  it("Test 5: click events appear in manualCaptures array with eventName, trigger, and captureSnippet — NOT as comments in captureCode", () => {
    const injections = generateAnalyticsInjections([pageWithLoadAndClick]);
    const injection = injections[0];
    expect(injection.manualCaptures).toHaveLength(1);
    expect(injection.manualCaptures[0].eventName).toBe("button_clicked");
    expect(injection.manualCaptures[0].trigger).toBe("click");
    expect(injection.captureCode).not.toContain("button_clicked"); // not in captureCode
    expect(injection.captureCode).not.toContain("// TODO"); // no comment markers
  });

  it("Test 6: manualCaptures captureSnippet is copy-paste ready with property keys", () => {
    const injections = generateAnalyticsInjections([pageWithLoadAndClick]);
    const snippet = injections[0].manualCaptures[0].captureSnippet;
    expect(snippet).toContain('posthog?.capture("button_clicked"');
    expect(snippet).toContain("button_label"); // property key included
  });

  it("Test 7: page with 0 events returns no AnalyticsInjection", () => {
    const injections = generateAnalyticsInjections([pageWithNoEvents]);
    expect(injections).toHaveLength(0);
  });

  it("Test 8: multiple pages produce separate AnalyticsInjection per page", () => {
    const injections = generateAnalyticsInjections([pageWithLoadAndClick, pageWithLoadOnly]);
    expect(injections).toHaveLength(2);
    expect(injections[0].pageName).toBe("Dashboard");
    expect(injections[1].pageName).toBe("Settings");
  });

  it("Test 9: pages with 0 events are skipped, only pages with events returned", () => {
    const injections = generateAnalyticsInjections([pageWithLoadAndClick, pageWithNoEvents, pageWithLoadOnly]);
    expect(injections).toHaveLength(2);
  });

  it("Test 12: importCode includes useRef alongside useEffect and usePostHog", () => {
    const injections = generateAnalyticsInjections([pageWithLoadAndClick]);
    expect(injections[0].importCode).toContain("useRef");
    expect(injections[0].importCode).toContain("useEffect");
    expect(injections[0].importCode).toContain("usePostHog");
  });

  it("submit events appear in manualCaptures, mount events in captureCode", () => {
    const injections = generateAnalyticsInjections([pageWithSubmit]);
    expect(injections).toHaveLength(1);
    const injection = injections[0];
    // submit -> manualCaptures
    expect(injection.manualCaptures.some((mc) => mc.trigger === "submit")).toBe(true);
    // mount -> captureCode
    expect(injection.captureCode).toContain("login_page_loaded");
  });
});

describe("buildProviderCode", () => {
  it("Test 9: returns PostHogProvider wrapper code with posthog import and VITE_POSTHOG_API_KEY guard", () => {
    const code = buildProviderCode();
    expect(code).toContain('import posthog from "posthog-js"');
    expect(code).toContain('import { PostHogProvider } from "posthog-js/react"');
    expect(code).toContain("VITE_POSTHOG_API_KEY");
    expect(code).toContain("posthog.init");
    expect(code).toContain("PostHogProvider");
  });
});

describe("buildIdentifyCode", () => {
  it("Test 10: firebase provider returns useEffect with posthog.identify and posthog.reset", () => {
    const code = buildIdentifyCode("firebase");
    expect(code).toContain("posthog.identify");
    expect(code).toContain("posthog.reset()");
    expect(code).toContain("useEffect");
    expect(code).toContain("user.email");
  });

  it("Test 11: null auth provider returns empty string", () => {
    const code = buildIdentifyCode(null);
    expect(code).toBe("");
  });

  it("passport provider returns useEffect with posthog.identify and posthog.reset", () => {
    const code = buildIdentifyCode("passport");
    expect(code).toContain("posthog.identify");
    expect(code).toContain("posthog.reset()");
  });
});
