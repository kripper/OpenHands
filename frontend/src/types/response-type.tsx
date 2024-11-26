import { ActionMessage, LogMessage, ObservationMessage, StatusMessage } from "./message";

type SocketMessage = ActionMessage | ObservationMessage | LogMessage | StatusMessage;

export { type SocketMessage };
