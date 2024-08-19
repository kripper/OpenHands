import { ActionMessage, LogMessage, ObservationMessage } from "./Message";

type SocketMessage = ActionMessage | ObservationMessage | LogMessage;

export { type SocketMessage };
