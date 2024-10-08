import ActionType from "#/types/ActionType";

export function sendTerminalCommand(command: string) {
  // replace ^c character when copied from terminal
  // eslint-disable-next-line no-control-regex
  const cleanedCommand = command.replace(/\u0003\b/, "");
  if (!cleanedCommand) return;
  const event = { action: ActionType.RUN, args: { command: cleanedCommand } };
  return JSON.stringify(event);
}
