import meetTheCli from "./lessons/meet-the-cli.json";
import networkFoundations from "./lessons/network-foundations.json";
import learnSwitching from "./lessons/learn-switching.json";

export const cliLabCompartments = [meetTheCli, networkFoundations, learnSwitching];

export const cliLessons = cliLabCompartments.flatMap((compartment) =>
  (compartment.lessons || []).map((lesson, index) => ({
    ...lesson,
    compartmentId: compartment.compartmentId,
    compartmentTitle: compartment.compartmentTitle,
    vendorId: compartment.vendorId,
    topology: lesson.topology || compartment.sharedTopology,
    orderIndex: index + 1,
  }))
);

export function findCliLesson(labId) {
  return cliLessons.find((lesson) => lesson.id === labId);
}

export function nextCliLesson(labId) {
  const current = findCliLesson(labId);
  if (!current?.nextLabId) return null;
  return findCliLesson(current.nextLabId);
}
