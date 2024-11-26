import { useDispatch, useSelector } from "react-redux";
import React from "react";
import posthog from "posthog-js";
import { convertImageToBase64 } from "#/utils/convert-image-to-base-64";
import { ChatMessage } from "./chat-message";
import { FeedbackActions } from "./feedback-actions";
import { ImageCarousel } from "./image-carousel";
import { createChatMessage, createRegenerateLastMessage } from "#/services/chat-service";
import { InteractiveChatBox } from "./interactive-chat-box";
import { addUserMessage, removeLastAssistantMessage } from "#/state/chat-slice";
import { RootState } from "#/store";
import AgentState from "#/types/agent-state";
import { generateAgentStateChangeEvent } from "#/services/agent-state-service";
import { FeedbackModal } from "./feedback-modal";
import { useScrollToBottom } from "#/hooks/use-scroll-to-bottom";
import TypingIndicator from "./chat/typing-indicator";
import ConfirmationButtons from "./chat/confirmation-buttons";
import { ErrorMessage } from "./error-message";
import { ContinueButton } from "./continue-button";
import { ScrollToBottomButton } from "./scroll-to-bottom-button";
import { Suggestions } from "./suggestions";
import { SUGGESTIONS } from "#/utils/suggestions";
import { IoMdChatbubbles } from "react-icons/io";
import beep from "#/utils/beep";
import { I18nKey } from "#/i18n/declaration";
import { useTranslation } from "react-i18next";
import VolumeIcon from "./VolumeIcon";
import { FaSyncAlt } from "react-icons/fa";


import BuildIt from "#/icons/build-it.svg?react";
import {
  useWsClient,
  WsClientProviderStatus,
} from "#/context/ws-client-provider";
import OpenHands from "#/api/open-hands";
import { downloadWorkspace } from "#/utils/download-workspace";
import { SuggestionItem } from "./suggestion-item";
import { useAuth } from "#/context/auth-context";

const isErrorMessage = (
  message: Message | ErrorMessage,
): message is ErrorMessage => "error" in message;

export function ChatInterface() {
  const { gitHubToken } = useAuth();
  const { send, status, isLoadingMessages } = useWsClient();

  const dispatch = useDispatch();
  const scrollRef = React.useRef<HTMLDivElement>(null);
  const { scrollDomToBottom, onChatBodyScroll, hitBottom } =
    useScrollToBottom(scrollRef);

  const { messages } = useSelector((state: RootState) => state.chat);
  const { curAgentState } = useSelector((state: RootState) => state.agent);

  const [feedbackPolarity, setFeedbackPolarity] = React.useState<
    "positive" | "negative"
  >("positive");
  const [feedbackModalIsOpen, setFeedbackModalIsOpen] = React.useState(false);
  const [messageToSend, setMessageToSend] = React.useState<string | null>(null);
  const [autoMode, setAutoMode] = React.useState(false);
  const [isDownloading, setIsDownloading] = React.useState(false);
  const [hasPullRequest, setHasPullRequest] = React.useState(false);

  React.useEffect(() => {
    if (status === WsClientProviderStatus.ACTIVE) {
      try {
        OpenHands.getRuntimeId().then(({ runtime_id }) => {
          // eslint-disable-next-line no-console
          console.log(
            "Runtime ID: %c%s",
            "background: #444; color: #ffeb3b; font-weight: bold; padding: 2px 4px; border-radius: 4px;",
            runtime_id,
          );
        });
      } catch (e) {
        console.warn("Runtime ID not available in this environment");
      }
    }
  }, [status]);

  const handleSendMessage = async (content: string, dispatchContent: string = "", files: File[]) => {
    posthog.capture("user_message_sent", {
      current_message_count: messages.length,
    });
    const promises = files.map((file) => convertImageToBase64(file));
    const imageUrls = await Promise.all(promises);

    const timestamp = new Date().toISOString();
    dispatch(addUserMessage({ content: dispatchContent || content, imageUrls, timestamp }));
    send(createChatMessage(content, imageUrls, timestamp));
    setMessageToSend(null);
  };

  const handleStop = () => {
    posthog.capture("stop_button_clicked");
    send(generateAgentStateChangeEvent(AgentState.STOPPED));
  };

  const handleSendContinueMsg = () => {
    handleSendMessage("Continue", "", []);
  };
  const { t } = useTranslation();

  const handleAutoMsg = () => {
    handleSendMessage(
      t(I18nKey.CHAT_INTERFACE$AUTO_MESSAGE),
      t(I18nKey.CHAT_INTERFACE$INPUT_AUTO_MESSAGE),
      [],
    );
  };

  const handleRegenerateClick = () => {
    dispatch(removeLastAssistantMessage());
    send(createRegenerateLastMessage());
  };

  const onClickShareFeedbackActionButton = async (
    polarity: "positive" | "negative",
  ) => {
    setFeedbackModalIsOpen(true);
    setFeedbackPolarity(polarity);
  };
  React.useEffect(() => {
    if (autoMode && curAgentState === AgentState.AWAITING_USER_INPUT) {
      handleAutoMsg();
    }
  }, [autoMode, curAgentState]);

  React.useEffect(() => {
    if (
      (!autoMode && curAgentState === AgentState.AWAITING_USER_INPUT) ||
      curAgentState === AgentState.ERROR ||
      curAgentState === AgentState.FINISHED
    ) {
      if (localStorage["is_muted"] !== "true") beep();
    }
  }, [curAgentState]);

  const handleDownloadWorkspace = async () => {
    setIsDownloading(true);
    try {
      await downloadWorkspace();
    } catch (error) {
      // TODO: Handle error
    } finally {
      setIsDownloading(false);
    }
  };

  let chatInterface = (
    <div className="h-full flex flex-col justify-between" style={{ height: "94%" }}>
      {messages.length === 0 && (
        <div className="flex flex-col gap-6 h-full px-4 items-center justify-center">
          <div className="flex flex-col items-center p-4 bg-neutral-700 rounded-xl w-full">
            <BuildIt width={45} height={54} />
            <span className="font-semibold text-[20px] leading-6 -tracking-[0.01em] gap-1">
              Let&apos;s start building!
            </span>
          </div>
          <Suggestions
            suggestions={Object.entries(SUGGESTIONS.repo)
              .slice(0, 0)
              .map(([label, value]) => ({
                label,
                value,
              }))}
            onSuggestionClick={(value) => {
              setMessageToSend(value);
            }}
          />
        </div>
      )}

      <div
        ref={scrollRef}
        onScroll={(e) => onChatBodyScroll(e.currentTarget)}
        className="flex flex-col grow overflow-y-auto overflow-x-hidden px-4 pt-4 gap-2"
      >
        {isLoadingMessages && (
          <div className="flex justify-center">
            <div className="w-6 h-6 border-2 border-t-[4px] border-primary-500 rounded-full animate-spin" />
          </div>
        )}

        {!isLoadingMessages &&
          messages.map((message, index) =>
            isErrorMessage(message) ? (
              <ErrorMessage
                key={index}
                id={message.id}
                message={message.message}
              />
            ) : (
              <ChatMessage
                key={index}
                type={message.sender}
                message={message.content}
              >
                {message.imageUrls.length > 0 && (
                  <ImageCarousel size="small" images={message.imageUrls} />
                )}
                {messages.length - 1 === index &&
                  message.sender === "assistant" &&
                  curAgentState === AgentState.AWAITING_USER_CONFIRMATION && (
                    <ConfirmationButtons />
                  )}
              </ChatMessage>
            ),
          )}

        {(curAgentState === AgentState.FINISHED && false) && (
          <div className="flex flex-col gap-2 mb-2">
            {gitHubToken ? (
              <div className="flex flex-row gap-2 justify-center w-full">
                {!hasPullRequest ? (
                  <>
                    <SuggestionItem
                      suggestion={{
                        label: "Push to Branch",
                        value:
                          "Please push the changes to a remote branch on GitHub, but do NOT create a pull request.",
                      }}
                      onClick={(value) => {
                        posthog.capture("push_to_branch_button_clicked");
                        handleSendMessage(value, "", []);
                      }}
                    />
                    <SuggestionItem
                      suggestion={{
                        label: "Push & Create PR",
                        value:
                          "Please push the changes to GitHub and open a pull request.",
                      }}
                      onClick={(value) => {
                        posthog.capture("create_pr_button_clicked");
                        handleSendMessage(value, "", []);
                        setHasPullRequest(true);
                      }}
                    />
                  </>
                ) : (
                  <SuggestionItem
                    suggestion={{
                      label: "Push changes to PR",
                      value:
                        "Please push the latest changes to the existing pull request.",
                    }}
                    onClick={(value) => {
                      posthog.capture("push_to_pr_button_clicked");
                      handleSendMessage(value, "", []);
                    }}
                  />
                )}
              </div>
            ) : (
              <SuggestionItem
                suggestion={{
                  label: !isDownloading
                    ? "Download .zip"
                    : "Downloading, please wait...",
                  value: "Download .zip",
                }}
                onClick={() => {
                  posthog.capture("download_workspace_button_clicked");
                  handleDownloadWorkspace();
                }}
              />
            )}
          </div>
        )}
      </div>

      <div className="flex flex-col gap-[6px] px-4 pb-4">
        <div className="flex justify-between relative">
          <div className="flex gap-1">
            <FeedbackActions
              onPositiveFeedback={() =>
                onClickShareFeedbackActionButton("positive")
              }
              onNegativeFeedback={() =>
                onClickShareFeedbackActionButton("negative")
              }
            />
            <button
              style={{
                width: "25%",
              }}
              type="button"
              onClick={handleRegenerateClick}
              className="p-1 bg-neutral-700 border border-neutral-600 rounded hover:bg-neutral-500"
            >
              <div style={{ top: "-2px", position: "relative" }}>
                {<FaSyncAlt className="inline mr-2 w-3 h-3" />}
              </div>
            </button>
          </div>
          <div className="absolute left-1/2 transform -translate-x-1/2 bottom-0">
            {messages.length > 2 &&
              curAgentState === AgentState.AWAITING_USER_INPUT && (
                <ContinueButton onClick={handleSendContinueMsg} />
              )}
            {curAgentState === AgentState.RUNNING && <TypingIndicator />}
          </div>
          {!hitBottom && <ScrollToBottomButton onClick={scrollDomToBottom} />}
        </div>

        <InteractiveChatBox
          onSubmit={handleSendMessage}
          onStop={handleStop}
          isDisabled={
            curAgentState === AgentState.LOADING ||
            curAgentState === AgentState.AWAITING_USER_CONFIRMATION
          }
          mode={curAgentState === AgentState.RUNNING ? "stop" : "submit"}
          value={messageToSend ?? undefined}
          onChange={setMessageToSend}
        />
      </div>

      <FeedbackModal
        isOpen={feedbackModalIsOpen}
        onClose={() => setFeedbackModalIsOpen(false)}
        polarity={feedbackPolarity}
      />
    </div>
  );
  chatInterface = (
    <div className="flex flex-col h-full bg-neutral-800">
      <div className="flex items-center gap-2 border-b border-neutral-600 text-sm px-4 py-2"
        style={{
          position: "sticky",
          top: "0px",
          zIndex: "10",
          background: "rgb(38 38 38 / var(--tw-bg-opacity))",
        }}
      >
        <IoMdChatbubbles />
        Chat
        <div className="ml-auto">
          <label className="flex items-center space-x-2">
            <input
              type="checkbox"
              checked={autoMode}
              onChange={() => setAutoMode(!autoMode)}
              aria-label="Auto Mode"
          />
          <span>Auto Mode</span>
        </label>
        </div>
        <VolumeIcon />

      </div>
      {chatInterface}
    </div>
  );
  return chatInterface;
}
