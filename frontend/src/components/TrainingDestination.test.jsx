import { cleanup, render, screen } from "@testing-library/react";
import { afterEach } from "vitest";
import { describe, expect, it, vi } from "vitest";
import { TrainingDestination } from "./TrainingDestination";

vi.mock("react-router-dom", () => ({ Link: ({ to, children }) => <span data-testid="spa-link" data-to={to}>{children}</span> }));
afterEach(cleanup);

describe("cross-application training destinations", () => {
  it.each(["INC2511", "INC2404"])("uses a document navigation for %s", (ticket) => {
    const route = `/service-desk/tickets/${ticket}?returnTo=%2Ftraining%2Fmodule%2Fmodule.endpoint.pc_hardware`;
    render(<TrainingDestination activity={{ activity_type: "service_desk_scenario", destination_route: route }}>Continue</TrainingDestination>);
    expect(screen.getByRole("link", { name: "Continue" })).toHaveAttribute("href", route);
    expect(screen.queryByTestId("spa-link")).not.toBeInTheDocument();
  });

  it("keeps Nexus destinations inside the SPA", () => {
    render(<TrainingDestination activity={{ activity_type: "quiz", destination_route: "/quizzes/78" }}>Take quiz</TrainingDestination>);
    expect(screen.getByTestId("spa-link")).toHaveAttribute("data-to", "/quizzes/78");
  });
});
