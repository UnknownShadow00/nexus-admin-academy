// Synthetic API contract fixtures. Never imports backend code or touches a DB.
export const stats = { name: 'Taylor', level_name: 'IT Explorer', total_xp: 420, streak: 3 };
export const certification = { key: 'comptia-aplus', name: 'CompTIA A+', version: { key: 'phase1_fixture' } };
export const module = { key: 'module.aplus.core1.ip_configuration', title: 'IP Configuration & Basic Connectivity Troubleshooting', description: 'Build a reliable troubleshooting process.' };
export const lesson = { key: 'lesson.ipv4', title: 'IPv4 Configuration Basics', summary: 'Understand the connection before changing it.', content_markdown: 'Read the IP configuration and identify the next safe check.\n\n`ipconfig` shows the local configuration.', progress: { status: 'in_progress' }, resources: [] };
export const continuation = { kind: 'lesson', title: lesson.title, status: 'in_progress', label: 'Continue learning', route: `/learning-v2/modules/${module.key}/lessons/${lesson.key}`, available: true, estimated_minutes: 12 };
export const progress = { status: 'in_progress', module_complete: false, lessons: { completed: 2, total: 5 }, quick_checks: { completed: 1, total: 5 } };
export const current = { certification, module, progress, continue: continuation, locked: false };
export const learning = { current, modules: [current], corrections: [] };
export const moduleDetail = { ...current, lessons: [lesson], assessments: [], interactions: [], explain_prompts: [], module_resources: [] };
export const lessonDetail = { certification, module, lesson, interactions: [], previous_lesson_key: null, next_lesson_key: null };
export const legacyModule = { stable_id: 'module.orientation.nexus', title: 'Nexus Orientation', route: '/training/module/module.orientation.nexus', required_complete: 1, required_total: 3, status: 'in_progress', completion_percent: 33, locked: false, purpose: 'Get familiar with your training workspace.' };
export const legacyActivity = { title: 'Welcome to Nexus', activity_label: 'Lesson', activity_type: 'lesson', destination_route: '/lessons/900001', estimated_minutes: 8 };
export const training = { current_stage: { stable_id: 'stage.orientation', title: 'Orientation' }, current_module: legacyModule, next_activity: legacyActivity, current_activity: legacyActivity, stages: [] };
const metric = { completed: 0, total: 1, percent: 0 };
export const trainingProgress = { current_module: legacyModule, overall_training: metric, videos: metric, quizzes: metric, practice: metric, guided_labs: metric, service_desk: metric, modules_completed: 0, total_modules: 1, skills: [] };
export const student = (legacy = false) => ({ student_id: legacy ? 900002 : 900001, name: 'Taylor', email: '', is_mentor: false, must_change_password: false });
