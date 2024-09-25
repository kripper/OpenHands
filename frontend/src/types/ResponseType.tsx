import { ActionMessage, LogMessage, ObservationMessage } from "./Message";

type SocketMessage = ActionMessage | ObservationMessage | LogMessage | StatusMessage;

export { type SocketMessage };
