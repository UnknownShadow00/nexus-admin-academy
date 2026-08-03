import {
  IconAdjustments,
  IconBell,
  IconInfoCircle,
  IconSparkles,
} from '@tabler/icons-react';
import { Priority } from '@service-desk/shared';
import type { ReactNode } from 'react';
import {
  Badge,
  Button,
  Card,
  CardHeader,
  IconButton,
  Input,
  Modal,
  PanelFrame,
  PriorityBadge,
  Tabs,
  TabsContent,
  TabsList,
  TabsTrigger,
  Tooltip,
} from '@service-desk/ui';

const sectionClass =
  'rounded-md border border-zinc-800 bg-zinc-900/60 p-4 sm:p-5';

export default function DesignSystemPage() {
  return (
    <main className="mx-auto min-h-screen max-w-7xl p-4 sm:p-6 md:p-8">
      <header className="mb-8 border-b border-zinc-800 pb-5">
        <p className="font-label text-xs font-extrabold uppercase text-sky-400">
          Phase 1 visual smoke route
        </p>
        <h1 className="mt-2 font-display text-2xl font-bold text-zinc-100 sm:text-3xl">
          Design system
        </h1>
        <p className="mt-2 max-w-2xl text-sm text-zinc-400">
          A responsive inventory of the reusable interface primitives.
        </p>
      </header>

      <div className="grid gap-4 lg:grid-cols-2">
        <section className={sectionClass}>
          <ShowroomTitle>Buttons</ShowroomTitle>
          <div className="flex flex-wrap items-center gap-3">
            <Button variant="primary">Primary</Button>
            <Button variant="light">Light</Button>
            <Button variant="soft">Soft</Button>
            <Button variant="default">Default</Button>
          </div>
          <div className="mt-5 flex items-center gap-3">
            <IconButton aria-label="Notifications">
              <IconBell aria-hidden="true" className="h-5 w-5" />
            </IconButton>
            <Tooltip content="Adjust display" delayDuration={0}>
              <IconButton aria-label="Display settings">
                <IconAdjustments aria-hidden="true" className="h-5 w-5" />
              </IconButton>
            </Tooltip>
            <span className="text-sm text-zinc-400">IconButton + Tooltip</span>
          </div>
        </section>

        <section className={sectionClass}>
          <ShowroomTitle>Inputs</ShowroomTitle>
          <label
            className="block text-xs font-bold uppercase text-zinc-400"
            htmlFor="sample-input"
          >
            Search label
          </label>
          <Input
            className="mt-2"
            id="sample-input"
            placeholder="Search the workspace"
          />
        </section>

        <section className={sectionClass}>
          <ShowroomTitle>Card and CardHeader</ShowroomTitle>
          <Card>
            <CardHeader title="Open requests" meta="6 items" />
            <div className="p-4 text-sm text-zinc-400">
              Card content uses compact spacing and a restrained surface
              hierarchy.
            </div>
          </Card>
        </section>

        <section className={sectionClass}>
          <ShowroomTitle>Badges</ShowroomTitle>
          <div className="flex flex-wrap gap-2">
            <Badge>Default</Badge>
            <Badge variant="sky">Ready</Badge>
            <Badge variant="amber">Pending</Badge>
            <Badge variant="success">Online</Badge>
          </div>
          <div className="mt-4 flex flex-wrap gap-4">
            <PriorityBadge priority={Priority.Critical} />
            <PriorityBadge priority={Priority.High} />
            <PriorityBadge priority={Priority.Medium} />
            <PriorityBadge priority={Priority.Low} />
            <PriorityBadge pill priority={Priority.High}>
              High pill
            </PriorityBadge>
          </div>
        </section>

        <section className={sectionClass}>
          <ShowroomTitle>Tabs</ShowroomTitle>
          <Tabs defaultValue="overview">
            <TabsList aria-label="Preview tabs">
              <TabsTrigger value="overview">Overview</TabsTrigger>
              <TabsTrigger value="activity">Activity</TabsTrigger>
            </TabsList>
            <TabsContent value="overview">
              Overview content is active.
            </TabsContent>
            <TabsContent value="activity">
              Activity content is active.
            </TabsContent>
          </Tabs>
        </section>

        <section className={sectionClass}>
          <ShowroomTitle>Modal</ShowroomTitle>
          <p className="mb-4 text-sm text-zinc-400">
            Dialog behavior includes a focus trap, keyboard dismissal, and
            accessible labelling.
          </p>
          <Modal
            description="This is an isolated component preview."
            title="Modal heading"
            trigger={
              <Button variant="soft">
                <IconSparkles aria-hidden="true" className="h-4 w-4" />
                Open modal
              </Button>
            }
          >
            <div className="flex gap-3">
              <IconInfoCircle
                aria-hidden="true"
                className="h-5 w-5 shrink-0 text-sky-400"
              />
              <p className="text-sm text-zinc-300">
                Modal content stays readable at desktop and mobile widths.
              </p>
            </div>
          </Modal>
        </section>
      </div>

      <section className="mt-4">
        <ShowroomTitle>PanelFrame variants</ShowroomTitle>
        <div className="grid gap-3 sm:grid-cols-2">
          <PanelFrame variant="default">Default frame</PanelFrame>
          <PanelFrame variant="ad">Directory modifier</PanelFrame>
          <PanelFrame variant="assets">Assets modifier</PanelFrame>
          <PanelFrame variant="contained">Contained modifier</PanelFrame>
          <PanelFrame className="sm:col-span-2" variant="fab-clearance">
            Floating-action clearance modifier
          </PanelFrame>
        </div>
      </section>
    </main>
  );
}

function ShowroomTitle({ children }: Readonly<{ children: ReactNode }>) {
  return (
    <h2 className="mb-4 font-label text-sm font-extrabold uppercase text-zinc-200">
      {children}
    </h2>
  );
}
