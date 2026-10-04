import { cleanup, render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it } from "vitest";
import Banner from "./Banner";

afterEach(cleanup);

describe("Banner notices", () => {
  it.each(["info", "success", "warning"])("announces %s feedback as status", (variant) => {
    render(<Banner variant={variant}>{variant} feedback</Banner>);
    expect(screen.getByRole("status")).toHaveTextContent(`${variant} feedback`);
  });

  it("announces an error immediately", () => {
    render(<Banner variant="error">Could not save</Banner>);
    expect(screen.getByRole("alert")).toHaveTextContent("Could not save");
  });
});
