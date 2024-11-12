import ActionType from "#/types/ActionType";
// import Session from "./session";

export function createChatMessage(
  message: string,
  images_urls: string[],
  timestamp: string,
) {
  const event = {
    action: ActionType.MESSAGE,
    args: { content: message, images_urls, timestamp },
  };
  return event;
}

export function createRegenerateLastMessage(): string {
  const event = {
    action: ActionType.REGENERATE,
    args: {},
  };
  const eventString = JSON.stringify(event);
  return eventString;
}

export function createJupyterCode(code: string): string {
  const event = {
    action: ActionType.RUN_IPYTHON,
    args: { code },
  };
  const eventString = JSON.stringify(event);
  return eventString;
}
