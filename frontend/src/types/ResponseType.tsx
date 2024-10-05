import { ActionMessage, LogMessage, ObservationMessage, StatusMessage } from "./Message";

type SocketMessage = ActionMessage | ObservationMessage | LogMessage | StatusMessage;

export { type SocketMessage };
