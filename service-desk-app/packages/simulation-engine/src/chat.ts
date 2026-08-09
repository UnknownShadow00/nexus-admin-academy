import type { ChatThreadOverlay } from './types';

export interface ScriptedChatReply {
  triggerKey: string;
  body: string;
}

interface ChatReplyRule extends ScriptedChatReply {
  keywords: readonly string[];
}

export const CHAT_REPLY_RULES: readonly ChatReplyRule[] = [
  {
    triggerKey: 'confirm-location',
    keywords: ['address', 'location', 'where should'],
    body: 'Thanks for checking. Please use the office location shown in my directory profile, and let me know if you need a floor or desk reference.',
  },
  {
    triggerKey: 'confirm-device',
    keywords: [
      'asset',
      'computer',
      'device',
      'headset',
      'laptop',
      'scanner',
      'workstation',
    ],
    body: 'Yes, the device listed on my directory profile is the one involved. I can keep it available while you run the next check.',
  },
  {
    triggerKey: 'confirm-delivery',
    keywords: ['arrived', 'delivered', 'delivery', 'received'],
    body: 'I can confirm the handoff is complete and the item arrived with me. Everything in the package appears to be present.',
  },
  {
    triggerKey: 'confirm-access-retest',
    keywords: [
      'access',
      'calendar',
      'login',
      'sign in',
      'sign-in',
      'verification',
    ],
    body: 'I have tried again in a fresh session. The latest access change is showing now, and I can continue with my work.',
  },
] as const;

const GENERIC_REPLY: ScriptedChatReply = {
  triggerKey: 'general-acknowledgement',
  body: 'Thanks for the update. I am available if you need me to confirm another detail or test the next step.',
};

export function resolveScriptedChatReply(body: string): ScriptedChatReply {
  const normalizedBody = body.trim().toLowerCase();
  const matchingRule = CHAT_REPLY_RULES.find((rule) =>
    rule.keywords.some((keyword) => normalizedBody.includes(keyword)),
  );

  return matchingRule
    ? { triggerKey: matchingRule.triggerKey, body: matchingRule.body }
    : GENERIC_REPLY;
}

export function isChatThreadUnread(thread: ChatThreadOverlay) {
  const lastReadTime = thread.lastReadAt
    ? new Date(thread.lastReadAt).getTime()
    : Number.NEGATIVE_INFINITY;

  return thread.messages.some(
    (message) =>
      !message.fromStudent &&
      new Date(message.createdAt).getTime() > lastReadTime,
  );
}
