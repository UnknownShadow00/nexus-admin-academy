import { cleanup, render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it } from "vitest";
import PageContainer from "./PageContainer";

afterEach(cleanup);

describe("PageContainer", () => {
  it.each(["reading", "standard", "workspace"])("supports the %s page width", (width) => {
    render(<PageContainer width={width}><h1>{width} page</h1></PageContainer>);
    expect(screen.getByRole("main")).toHaveClass(`page-container-${width}`);
  });

  it("uses a safe default for unknown widths and permits a non-main region", () => {
    render(<PageContainer as="section" width="unknown" aria-label="Course section">Content</PageContainer>);
    expect(screen.getByRole("region", { name: "Course section" })).toHaveClass("page-container-standard");
  });
});
