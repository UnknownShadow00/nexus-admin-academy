# Database Plan

Prisma/PostgreSQL schema plan, grouped by domain. Field lists are the plan-level contract Codex should implement in `packages/database/prisma/schema.prisma`; exact column types/indexes are decided at implementation time but the entities, relations, and the **global vs. per-attempt** split below are load-bearing and must not be reshuffled without updating ARCHITECTURE.md §3.

## Global vs. per-attempt — the rule

Two kinds of data:

1. **Global / template data** — owned by the platform (or a teacher, for custom scenarios), versioned, read by every attempt, never mutated by student actions. Directory roster, servers, KB articles, scenario definitions, achievement definitions.
2. **Per-attempt data** — created fresh (empty) when an `Attempt` starts, mutated only through `simulation-engine`'s `applyAction()`, isolated per student/attempt. Never shared across attempts.

Per-attempt tables do **not** duplicate the full 83-row directory template per student. Instead, per-attempt tables store only **overlays/deltas** (rows that exist *because* the student changed something) plus **attempt-scoped instances** for things that are inherently created during play (a `DeploymentRun`, a `ProvisionedDevice`, a `Shipment`). Reading "the current directory" for an attempt = template rows **left-joined** with that attempt's `DirectoryUserOverlay` rows, overlay wins if present. This is documented per-table below.

---

## 1. Identity, accounts, organizations

```prisma
model Account {
  id            String   @id @default(cuid())
  email         String   @unique
  passwordHash  String?               // null if OAuth-only
  displayName   String
  avatarEmoji   String?               // matches Settings' emoji-picker pattern, PRODUCT_MAP.md §19.2
  role          AccountRole           // STUDENT | TEACHER | ADMIN
  createdAt     DateTime @default(now())
  student       Student?
  teacher       Teacher?
  admin         Admin?
}

enum AccountRole { STUDENT TEACHER ADMIN }

model Student {
  id            String   @id @default(cuid())
  accountId     String   @unique
  account       Account  @relation(fields: [accountId], references: [id])
  organizationId String?
  organization  Organization? @relation(fields: [organizationId], references: [id])
  planId        String?               // current Plan (Free/Pro), see §7
  points        Int      @default(0)  // denormalized cache of latest Grade rollup — always re-derivable from Event/Grade
  rankTier      String   @default("ROOKIE")
  createdAt     DateTime @default(now())
  attempts      Attempt[]
  enrollments   Enrollment[]
  achievements  StudentAchievement[]
  friendships   Friendship[]
}

model Teacher {
  id             String   @id @default(cuid())
  accountId      String   @unique
  account        Account  @relation(fields: [accountId], references: [id])
  organizationId String
  organization   Organization @relation(fields: [organizationId], references: [id])
  classrooms     Classroom[]
}

model Admin {
  id        String  @id @default(cuid())
  accountId String  @unique
  account   Account @relation(fields: [accountId], references: [id])
}

model Organization {
  id        String   @id @default(cuid())
  name      String
  createdAt DateTime @default(now())
  teachers  Teacher[]
  students  Student[]
  classrooms Classroom[]
}

model Classroom {
  id             String   @id @default(cuid())
  organizationId String
  organization   Organization @relation(fields: [organizationId], references: [id])
  teacherId      String
  teacher        Teacher  @relation(fields: [teacherId], references: [id])
  name           String
  joinCode       String   @unique   // "Join Class" short-code flow, PRODUCT_MAP.md §20
  createdAt      DateTime @default(now())
  enrollments    Enrollment[]
  assignments    Assignment[]
}

model Enrollment {
  id          String   @id @default(cuid())
  classroomId String
  classroom   Classroom @relation(fields: [classroomId], references: [id])
  studentId   String
  student     Student  @relation(fields: [studentId], references: [id])
  joinedAt    DateTime @default(now())
  @@unique([classroomId, studentId])
}

model Assignment {
  id            String   @id @default(cuid())
  classroomId   String
  classroom     Classroom @relation(fields: [classroomId], references: [id])
  scenarioId    String
  scenario      Scenario @relation(fields: [scenarioId], references: [id])
  dueAt         DateTime?
  createdAt     DateTime @default(now())
}
```

**Global**: `Organization`, `Classroom` (structure), `Assignment` (definition). **Per-attempt**: none directly — `Enrollment` is a durable membership record, not attempt state.

## 2. Environment templates (global, versioned)

```prisma
model EnvironmentTemplate {
  id          String   @id @default(cuid())
  name        String                     // e.g. "Default Corp Org v1"
  version     Int      @default(1)
  publishedAt DateTime?                  // null = draft, editable; non-null = immutable
  directoryUsers DirectoryUserTemplate[]
  groups         GroupTemplate[]
  devices        DeviceTemplate[]
  servers        ServerTemplate[]
  assets         AssetTemplate[]
  licenses       LicenseTemplate[]
  kbArticles     KnowledgeBaseArticle[]
}

model DirectoryUserTemplate {
  id             String   @id @default(cuid())
  templateId     String
  template       EnvironmentTemplate @relation(fields: [templateId], references: [id])
  assetTag       String              // "SD1028" — shared key with DeviceTemplate, PRODUCT_MAP.md §8/§12
  fullName       String
  username       String
  jobTitle       String
  department     String
  locked         Boolean  @default(false)  // AD "account locked" starting state
  @@unique([templateId, assetTag])
}

model GroupTemplate {
  id           String   @id @default(cuid())
  templateId   String
  template     EnvironmentTemplate @relation(fields: [templateId], references: [id])
  name         String
  memberUserIds String[]           // DirectoryUserTemplate ids
}

model DeviceTemplate {
  id           String   @id @default(cuid())
  templateId   String
  template     EnvironmentTemplate @relation(fields: [templateId], references: [id])
  assetTag     String
  ownerUserId  String?             // DirectoryUserTemplate id
  deviceType   String              // "desktop" | "laptop" | "monitor" | ...
  status       String   @default("DEPLOYED")  // Asset Management's STATUS column, PRODUCT_MAP.md §12
}

model ServerTemplate {
  id           String   @id @default(cuid())
  templateId   String
  template     EnvironmentTemplate @relation(fields: [templateId], references: [id])
  hostname     String              // "DC01", "FILESERV01", ...
  role         String              // "Domain Controller" | "File Server" | "Mail Server" | "Print Server"
  location     String              // "SERVER ROOM A" | "SERVER ROOM B" | "LOBBY" | "CAFETERIA" — also covers NetworkDevice rows
  baselineCpuPct    Int
  baselineMemPct    Int
}

model AssetTemplate {
  id          String   @id @default(cuid())
  templateId  String
  template    EnvironmentTemplate @relation(fields: [templateId], references: [id])
  assetTag    String
  kind        String              // "HDMI Cable" | "Laptop" | "Monitor" | ... — Ship Manager's equipment list, PRODUCT_MAP.md §13
}

model LicenseTemplate {
  id          String   @id @default(cuid())
  templateId  String
  template    EnvironmentTemplate @relation(fields: [templateId], references: [id])
  productName String
  seatsTotal  Int
  assignedUserIds String[]
}

model KnowledgeBaseArticle {
  id         String   @id @default(cuid())
  templateId String
  template   EnvironmentTemplate @relation(fields: [templateId], references: [id])
  category   String              // one of the 10 categories, PRODUCT_MAP.md §11
  title      String
  body       String              // original content — never copy real site copy
  publishedAt DateTime @default(now())
}
```

**Global**: everything in this section, 100%. `ServerTemplate` also models the 8 "network devices" (routers/switches/firewall/APs) alongside the 5 servers from Server Room, PRODUCT_MAP.md §7 — differentiate with `role` values like `"Router"`/`"Switch"`/`"Firewall"`/`"WiFi AP"` vs. the server roles above; split into a separate `NetworkDeviceTemplate` model if the two need materially different fields once implementation starts.

## 3. Scenarios (global, versioned)

```prisma
model Scenario {
  id            String   @id @default(cuid())
  slug          String   @unique
  title         String
  category      String              // Network | Hardware | Software | Access | Security | Email — Analytics' Training Focus categories, PRODUCT_MAP.md §15
  priority      String              // Critical | High | Medium | Low
  environmentTemplateId String
  environmentTemplate    EnvironmentTemplate @relation(fields: [environmentTemplateId], references: [id])
  createdByTeacherId String?         // null = platform scenario; set = teacher-authored custom scenario
  activeVersionId String?  @unique
  versions      ScenarioVersion[]
  assignments   Assignment[]
}

model ScenarioVersion {
  id           String   @id @default(cuid())
  scenarioId   String
  scenario     Scenario @relation(fields: [scenarioId], references: [id])
  version      Int
  publishedAt  DateTime?           // null = draft
  incidentId   String              // "INC0012871"-style display id, generated per-attempt at start, not stored here as a constant
  requesterUserId String           // DirectoryUserTemplate id — the simulated requester
  description  String
  troubleshootingNotes String[]
  businessImpact String
  slaMinutes   Int
  pointValue   Int
  difficulty   String
  solutionType String              // "deployment" | "directory_action" | "chat_only" | ...
  targetEntityId String?           // DeviceTemplate/DirectoryUserTemplate id the objective targets
  explanation  String              // shown after close, "learning points"
  objectives   ScenarioObjective[]
  hints        ScenarioHint[]
  deploymentSteps DeploymentStepTemplate[]   // only populated for solutionType = "deployment"
}

model ScenarioObjective {
  id                String   @id @default(cuid())
  scenarioVersionId String
  scenarioVersion   ScenarioVersion @relation(fields: [scenarioVersionId], references: [id])
  order             Int
  description       String            // internal/teacher-facing description of what's checked
  predicateType     String            // discriminator: "directory_user_state" | "shipment_exists" | "chat_message_sent" | "deployment_completed" | ...
  predicateParams   Json              // typed per predicateType in simulation-engine, e.g. { field: "locked", equals: false }
  required          Boolean  @default(true)
  pointValue        Int
}

model ScenarioHint {
  id                String   @id @default(cuid())
  scenarioVersionId String
  scenarioVersion   ScenarioVersion @relation(fields: [scenarioVersionId], references: [id])
  order             Int
  text              String
  pointPenalty      Int      @default(0)
}

model DeploymentStepTemplate {
  id                String   @id @default(cuid())
  scenarioVersionId String
  scenarioVersion   ScenarioVersion @relation(fields: [scenarioVersionId], references: [id])
  order             Int                  // 1..11, PRODUCT_MAP.md §9
  stepType          String               // "cable_match" | "post_f12" | "boot_source" | "share_auth" | "hostname" | "task_sequence" | "reboot" | "domain_login"
  expectedAction    Json                 // e.g. { cables: {power:"power-port", ethernet:"eth-port", ...} }
  wrongActionResponses Json              // map of wrong-action-key -> copy shown (mirrors the exact inline-correction copy captured in complete-ticket-workflow.json)
}
```

**Global**: all of §3 — scenarios are authored content, versioned like the environment templates, never mutated by play.

## 4. Attempts (per-student, per-attempt) & the world-state overlay

```prisma
model Attempt {
  id            String   @id @default(cuid())
  studentId     String
  student       Student  @relation(fields: [studentId], references: [id])
  scenarioVersionId String
  scenarioVersion   ScenarioVersion @relation(fields: [scenarioVersionId], references: [id])
  assignmentId  String?             // set if started from a classroom Assignment
  incidentId    String              // generated at start, e.g. "INC0012871"
  status        AttemptStatus @default(ACTIVE)
  startedAt     DateTime @default(now())
  submittedAt   DateTime?
  supersededById String? @unique    // set when reset — points at the new Attempt

  directoryOverlays   DirectoryUserOverlay[]
  deploymentRuns      DeploymentRun[]
  provisionedDevices  ProvisionedDevice[]
  shipments           Shipment[]
  chatThreads         ChatThread[]
  events              Event[]
  grade               Grade?
}

enum AttemptStatus { ACTIVE SUBMITTED RESET EXPIRED }

// --- Per-attempt overlays: one row per template entity the student actually changed ---

model DirectoryUserOverlay {
  id             String   @id @default(cuid())
  attemptId      String
  attempt        Attempt  @relation(fields: [attemptId], references: [id])
  directoryUserTemplateId String
  locked         Boolean?           // null = inherit template value; non-null = override
  passwordReset  Boolean?
  groupChanges   Json?              // { added: [...], removed: [...] }
  updatedAt      DateTime @updatedAt
  @@unique([attemptId, directoryUserTemplateId])
}

// --- Per-attempt instances: created fresh during play, no template counterpart ---

model DeploymentRun {
  id            String   @id @default(cuid())
  attemptId     String
  attempt       Attempt  @relation(fields: [attemptId], references: [id])
  deviceType    String              // "desktop" | "laptop"
  currentStep   Int      @default(1)
  status        String   @default("IN_PROGRESS")   // IN_PROGRESS | COMPLETE | ABANDONED
  hostname      String?             // assigned SD#### once step 6 completes, must be unique across ALL attempts+templates (matches original's "cannot reuse an asset tag" rule, PRODUCT_MAP.md §9)
  startedAt     DateTime @default(now())
  completedAt   DateTime?
  @@unique([hostname])
}

model ProvisionedDevice {
  id              String   @id @default(cuid())
  attemptId       String
  attempt         Attempt  @relation(fields: [attemptId], references: [id])
  deploymentRunId String   @unique
  deploymentRun   DeploymentRun @relation(fields: [deploymentRunId], references: [id])
  assetTag        String              // == DeploymentRun.hostname
  shippedShipmentId String?  @unique  // set once shipped — leaves PC Shelf, PRODUCT_MAP.md §10
}

model Shipment {
  id               String   @id @default(cuid())
  attemptId        String
  attempt          Attempt  @relation(fields: [attemptId], references: [id])
  recipientUserId  String              // DirectoryUserTemplate id
  senderDepartment String
  addressLine1     String
  city             String
  state            String
  postalCode       String
  items            Json                // [{kind: "Laptop Charger", qty: 1}, ...] — matches Ship Manager's equipment list
  provisionedDeviceId String?
  speed            String              // STANDARD | EXPRESS | PRIORITY | RUSH
  returnLabelIncluded Boolean @default(false)
  shippedAt        DateTime @default(now())
}

model ChatThread {
  id            String   @id @default(cuid())
  attemptId     String
  attempt       Attempt  @relation(fields: [attemptId], references: [id])
  withUserId    String              // DirectoryUserTemplate id (the simulated requester/contact)
  pinned        Boolean  @default(false)
  messages      ChatMessage[]
}

model ChatMessage {
  id            String   @id @default(cuid())
  threadId      String
  thread        ChatThread @relation(fields: [threadId], references: [id])
  fromStudent   Boolean             // false = simulated NPC scripted reply
  body          String              // max 500 chars, matches original's input cap
  triggerKey    String?             // which scripted branch produced this (NPC messages only)
  createdAt     DateTime @default(now())
}
```

**Per-attempt, 100%**: everything in §4. `Attempt` is the root; every child row is scoped by `attemptId` and is created/mutated only via `simulation-engine.applyAction()` (ARCHITECTURE.md §3.4).

## 5. Events, grading, progress

```prisma
model Event {
  id          String   @id @default(cuid())
  attemptId   String
  attempt     Attempt  @relation(fields: [attemptId], references: [id])
  actorId     String              // Student.id, or Teacher.id for an override action
  type        String              // "directory.user_unlocked" | "deployment.step_completed" | "ticket.reveal_hint" | "ticket.closed_unresolved" | ...
  payload     Json
  success     Boolean  @default(true)   // false = rejected/invalid action attempt — still logged
  rejectReason String?
  createdAt   DateTime @default(now())
  @@index([attemptId, createdAt])
}
// INSERT-ONLY from application code. No update/delete mutations against this model anywhere in apps/api.

model Grade {
  id            String   @id @default(cuid())
  attemptId     String   @unique
  attempt       Attempt  @relation(fields: [attemptId], references: [id])
  pointsAwarded Int
  pointsPossible Int
  objectivesCompleted Json      // [{objectiveId, completedAt}]
  hintsUsed     Int      @default(0)
  penaltyPoints Int      @default(0)     // e.g. the observed -17 for unresolved close, PRODUCT_MAP.md §4
  resolved      Boolean
  computedAt    DateTime @default(now())
}
// Always recomputed by simulation-engine.evaluateObjectives() — never hand-edited.

model Progress {
  id             String   @id @default(cuid())
  studentId      String   @unique
  student        Student  @relation(fields: [studentId], references: [id])
  totalPoints    Int      @default(0)
  ticketsResolved Int     @default(0)
  accuracyPct    Int      @default(0)
  callVolume     Int      @default(0)
  categoryBreakdown Json             // per-category resolved counts, Analytics §15
  priorityBreakdown Json
  trainingFocus  Json                // which of the 6 categories are enabled — Analytics' toggle grid
  updatedAt      DateTime @default(now())
}
// Denormalized read-model, rebuilt from Event+Grade by a background job — never the source of truth.

model Achievement {
  id          String   @id @default(cuid())
  code        String   @unique       // "FIRST_TICKET", "SPEED_DEMON", ... — the 17 from PRODUCT_MAP.md §16
  name        String
  description String
  thresholdType String              // "tickets_resolved" | "calls_completed" | "login_streak" | "score" | "accuracy"
  thresholdValue Int
}

model StudentAchievement {
  id            String   @id @default(cuid())
  studentId     String
  student       Student  @relation(fields: [studentId], references: [id])
  achievementId String
  achievement   Achievement @relation(fields: [achievementId], references: [id])
  earnedAt      DateTime @default(now())
  @@unique([studentId, achievementId])
}

model CareerTier {
  id          String  @id @default(cuid())
  name        String              // "IT Support Foundations", ... — 4 tiers, PRODUCT_MAP.md §16
  pointThreshold Int
  order       Int
}
```

**Global**: `Achievement`, `CareerTier` (definitions). **Per-student (not per-attempt)**: `Progress`, `StudentAchievement` — these roll up across *all* of a student's attempts, not one. **Append-only, per-attempt**: `Event`, `Grade` (one final `Grade` per attempt, recomputed in place as objectives complete — the *history* of how it changed is reconstructable from `Event`, so `Grade` itself doesn't need its own versioning).

## 6. Social & communication

```prisma
model Friendship {
  id           String   @id @default(cuid())
  studentId    String
  student      Student  @relation(fields: [studentId], references: [id])
  friendStudentId String
  status       String   @default("PENDING")  // PENDING | ACCEPTED | DECLINED
  createdAt    DateTime @default(now())
  @@unique([studentId, friendStudentId])
}
```
Global relationship data (not per-attempt) — friends persist across attempts/scenarios, matching the real Cloud-Functions-backed `getFriends`/`getFriendRequests` evidence (network audit, §ARCHITECTURE.md).

## 7. Plans, quotas, subscriptions

```prisma
model Plan {
  id          String   @id @default(cuid())
  code        String   @unique     // "FREE" | "PRO"
  name        String
  priceMonthlyCents Int
  ticketsPerDay Int?               // null = unlimited (Pro)
  callsPerDay   Int?
}

model Subscription {
  id            String   @id @default(cuid())
  studentId     String   @unique
  student       Student  @relation(fields: [studentId], references: [id])
  planId        String
  plan          Plan     @relation(fields: [planId], references: [id])
  stripeCustomerId String?
  stripeSubscriptionId String?
  status        String              // "active" | "canceled" | "past_due"
  currentPeriodEnd DateTime?
}

model DailyQuotaUsage {
  id          String   @id @default(cuid())
  studentId   String
  student     Student  @relation(fields: [studentId], references: [id])
  date        DateTime              // truncated to day
  ticketsUsed Int      @default(0)
  callsUsed   Int      @default(0)
  @@unique([studentId, date])
}
```
Global/per-student (not per-attempt) — quotas and plan state track the student across their whole account, matching the header's persistent "N tickets left · resets in Xh Ym" chrome seen on every page in PRODUCT_MAP.md §1.

---

## Summary table: global vs. per-attempt

| Category | Models | Scope |
|---|---|---|
| Identity/org | `Account`, `Student`, `Teacher`, `Admin`, `Organization`, `Classroom`, `Enrollment`, `Assignment` | Durable, account/org-scoped |
| Environment templates | `EnvironmentTemplate`, `DirectoryUserTemplate`, `GroupTemplate`, `DeviceTemplate`, `ServerTemplate`, `AssetTemplate`, `LicenseTemplate`, `KnowledgeBaseArticle` | **Global**, versioned, immutable once published |
| Scenarios | `Scenario`, `ScenarioVersion`, `ScenarioObjective`, `ScenarioHint`, `DeploymentStepTemplate` | **Global**, versioned |
| Attempts & overlays | `Attempt`, `DirectoryUserOverlay`, `DeploymentRun`, `ProvisionedDevice`, `Shipment`, `ChatThread`, `ChatMessage` | **Per-attempt**, isolated |
| Events & grading | `Event`, `Grade` | **Per-attempt**, append-only |
| Rollups | `Progress`, `StudentAchievement` | **Per-student**, cross-attempt |
| Definitions | `Achievement`, `CareerTier`, `Plan` | **Global** |
| Account-scoped state | `Subscription`, `DailyQuotaUsage`, `Friendship` | **Per-student**, cross-attempt |

Reading "the current world state" for an attempt is always: `template rows (global) LEFT JOIN attempt overlay rows (per-attempt), overlay wins`. This single rule is what lets `packages/simulation-engine` stay simple and is the concrete implementation of ARCHITECTURE.md §3.1's copy-on-write design.
