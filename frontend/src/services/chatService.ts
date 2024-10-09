import ActionType from "#/types/ActionType";
import Session from "./session";

export function createChatMessage(
  message: string,
  images_urls: string[],
  timestamp: string,
) {
  const event = {
    action: ActionType.MESSAGE,
    args: { content: message, images_urls, timestamp },
  };
  return JSON.stringify(event);
}

export function regenerateLastMessage(): void {
  const event = {
    action: ActionType.REGENERATE,
    args: {},
  };
  const eventString = JSON.stringify(event);
  Session.send(eventString);
}

export function sendJupyterCode(code: string): void {
  const event = {
    action: ActionType.RUN_IPYTHON,
    args: { code },
  };
  const eventString = JSON.stringify(event);
  Session.send(eventString);
}
