import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

import { SUPPORTED_EVENT_IDS } from "../src/features/cli-labs/engine/commandEngine.js";
import { SUPPORTED_REQUIRED_STATE_KEYS } from "../src/features/cli-labs/engine/objectiveTracker.js";

const root = path.dirname(fileURLToPath(import.meta.url));
const lessonsDir = path.resolve(root, "../src/features/cli-labs/data/lessons");
const supportedEvents = new Set(SUPPORTED_EVENT_IDS);
const supportedStateKeys = new Set(SUPPORTED_REQUIRED_STATE_KEYS);
const supportedStepTypes = new Set(["explanation", "multiple-choice", "observe", "forward-decision", "hex-input", "frame-builder"]);
const errors = [];
const lessonIds = new Set();
const lessons = [];

function fail(message) {
  errors.push(message);
}

function readJson(filePath) {
  try {
    return JSON.parse(fs.readFileSync(filePath, "utf8"));
  } catch (error) {
    fail(`${filePath}: ${error.message}`);
    return null;
  }
}

function checkTrigger(trigger, location) {
  if (!trigger) {
    fail(`${location}: missing trigger`);
    return;
  }
  if (String(trigger).startsWith("regex:")) {
    try {
      new RegExp(String(trigger).slice("regex:".length), "i");
    } catch (error) {
      fail(`${location}: invalid regex trigger (${error.message})`);
    }
    return;
  }
  if (!supportedEvents.has(trigger)) {
    fail(`${location}: unsupported trigger "${trigger}"`);
  }
}

function isPermutation(values, length) {
  if (!Array.isArray(values) || values.length !== length) return false;
  const seen = new Set(values);
  return seen.size === length && values.every((value) => Number.isInteger(value) && value >= 0 && value < length);
}

function validateSteps(lesson, prefix, objectiveIds) {
  if (lesson.steps === undefined) return;
  if (!Array.isArray(lesson.steps)) {
    fail(`${prefix}: steps must be an array`);
    return;
  }

  const stepIds = new Set();
  for (const step of lesson.steps) {
    const stepId = step?.id || "(missing id)";
    const location = `${prefix}: step ${stepId}`;
    if (!step?.id) fail(`${location}: missing id`);
    if (step?.id && stepIds.has(step.id)) fail(`${location}: duplicate step id "${step.id}"`);
    if (step?.id) stepIds.add(step.id);
    if (!supportedStepTypes.has(step?.type)) fail(`${location}: unsupported type "${step?.type || ""}"`);

    if (step?.type === "multiple-choice" || step?.type === "forward-decision") {
      if (!Array.isArray(step.options) || step.options.length < 2) fail(`${location}: ${step.type} requires at least 2 options`);
      if (!Number.isInteger(step.correctIndex) || step.correctIndex < 0 || step.correctIndex >= (step.options || []).length) {
        fail(`${location}: ${step.type} has invalid correctIndex`);
      }
    }

    if (step?.type === "hex-input" && !String(step.answer || "").trim()) {
      fail(`${location}: hex-input requires answer`);
    }

    if (step?.type === "frame-builder") {
      if (!Array.isArray(step.fields) || !Array.isArray(step.correctOrder) || step.fields.length !== step.correctOrder.length) {
        fail(`${location}: frame-builder fields length must match correctOrder length`);
      } else if (!isPermutation(step.correctOrder, step.fields.length)) {
        fail(`${location}: frame-builder correctOrder must be a permutation of field indexes`);
      }
    }

    if (step?.type === "observe") {
      if (!Array.isArray(step.objectiveIds) || !step.objectiveIds.length) {
        fail(`${location}: observe requires objectiveIds`);
      } else {
        for (const objectiveId of step.objectiveIds) {
          if (!objectiveIds.has(objectiveId)) fail(`${location}: observe references unknown objective "${objectiveId}"`);
        }
      }
    }
  }
}

function validateLesson(lesson, sourceFile) {
  const prefix = `${sourceFile}:${lesson.id || "(missing id)"}`;
  if (!lesson.id) fail(`${prefix}: missing id`);
  if (!lesson.title) fail(`${prefix}: missing title`);
  if (lesson.id && lessonIds.has(lesson.id)) fail(`${prefix}: duplicate lesson id`);
  if (lesson.id) lessonIds.add(lesson.id);
  lessons.push(lesson);

  const objectiveIds = new Set();
  for (const objective of lesson.objectives || []) {
    if (!objective.id) fail(`${prefix}: objective missing id`);
    if (objective.id && objectiveIds.has(objective.id)) fail(`${prefix}: duplicate objective id "${objective.id}"`);
    if (objective.id) objectiveIds.add(objective.id);

    if (objective.miniObjectives?.length) {
      const miniIds = new Set();
      for (const mini of objective.miniObjectives) {
        if (!mini.id) fail(`${prefix}: mini objective missing id`);
        if (mini.id && miniIds.has(mini.id)) fail(`${prefix}: duplicate mini objective id "${mini.id}"`);
        if (mini.id) miniIds.add(mini.id);
        checkTrigger(mini.trigger, `${prefix}: mini objective ${mini.id || "(missing id)"}`);
      }
    } else {
      checkTrigger(objective.trigger, `${prefix}: objective ${objective.id || "(missing id)"}`);
    }
  }

  validateSteps(lesson, prefix, objectiveIds);

  const criteria = lesson.successCriteria || {};
  for (const key of Object.keys(criteria.requiredState || {})) {
    if (!supportedStateKeys.has(key)) {
      fail(`${prefix}: unsupported requiredState key "${key}"`);
    }
  }
  for (const command of criteria.requiredCommands || []) {
    if (!String(command).trim()) fail(`${prefix}: empty required command`);
  }
  if (criteria.requiredPcAction && !/^(ssh\s+\S+@\S+|ping\s+\S+)$/i.test(criteria.requiredPcAction)) {
    fail(`${prefix}: unsupported requiredPcAction "${criteria.requiredPcAction}"`);
  }
}

const files = fs.readdirSync(lessonsDir).filter((file) => file.endsWith(".json")).sort();
for (const file of files) {
  const payload = readJson(path.join(lessonsDir, file));
  if (!payload) continue;
  if (!payload.compartmentId) fail(`${file}: missing compartmentId`);
  if (!payload.vendorId) fail(`${file}: missing vendorId`);
  for (const lesson of payload.lessons || []) {
    validateLesson(lesson, file);
  }
}

for (const lesson of lessons) {
  if (lesson.nextLabId && !lessonIds.has(lesson.nextLabId)) {
    fail(`${lesson.id}: nextLabId "${lesson.nextLabId}" does not exist`);
  }
  if (lesson.nextLabId && lesson.nextLabId === lesson.id) {
    fail(`${lesson.id}: nextLabId points to itself`);
  }
}

if (errors.length) {
  console.error("CLI lab validation failed:");
  for (const error of errors) console.error(`- ${error}`);
  process.exit(1);
}

console.log(`CLI lab validation passed (${lessons.length} lessons across ${files.length} file(s)).`);
