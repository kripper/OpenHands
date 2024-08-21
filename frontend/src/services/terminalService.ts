import ActionType from "#/types/ActionType";
import Session from "./session";

export function sendTerminalCommand(command: string): void {
  // replace ^c character when copied from terminal
  // eslint-disable-next-line no-control-regex
  const cleanedCommand = command.replace(/\u0003\b/, "");
  if (!cleanedCommand) return;
  const event = { action: ActionType.RUN, args: { command: cleanedCommand } };
  const eventString = JSON.stringify(event);
  Session.send(eventString);
}
