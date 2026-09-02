import "vitest";

declare module "vitest" {
  interface Assertion<T = unknown> {
    toBeInTheDocument(): T;
    toBeDisabled(): T;
    toHaveBeenCalledOnce(): T;
  }
}
