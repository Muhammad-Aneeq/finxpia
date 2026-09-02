/**
 * Test setup for the dashboard render tests.
 *
 * `@testing-library/jest-dom` is deliberately not a dependency: the handful of matchers used
 * (`toBeInTheDocument`, `toBeDisabled`) are defined here instead, which keeps the frontend
 * dependency surface small for a static report site.
 */

import { expect } from "vitest";

expect.extend({
  toBeInTheDocument(received: Element | null) {
    const pass = received !== null && received.ownerDocument.contains(received);
    return {
      pass,
      message: () =>
        pass
          ? "expected element not to be in the document"
          : "expected element to be in the document, but it was not found",
    };
  },
  toBeDisabled(received: Element | null) {
    const pass = received instanceof HTMLElement && received.hasAttribute("disabled");
    return {
      pass,
      message: () =>
        pass ? "expected element not to be disabled" : "expected element to be disabled",
    };
  },
  toHaveBeenCalledOnce(received: { mock?: { calls: unknown[] } }) {
    const calls = received?.mock?.calls?.length ?? -1;
    return {
      pass: calls === 1,
      message: () => `expected exactly 1 call, received ${calls}`,
    };
  },
});
