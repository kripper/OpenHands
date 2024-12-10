import React from "react";
import { useParams } from "react-router";

interface ConversationContextType {
  conversationId: string;
}

const ConversationContext = React.createContext<ConversationContextType | null>(
  null,
);

export function ConversationProvider({
  children,
}: {
  children: React.ReactNode;
}) {
  const { conversationId } = useParams<{ conversationId: string }>();

  if (!conversationId) {
    throw new Error(
      "ConversationProvider must be used within a route that has a conversationId parameter",
    );
  }

  return (
    <ConversationContext.Provider value={{ conversationId }}>
      {children}
    </ConversationContext.Provider>
  );
}

export function useConversation() {
  const context = React.useContext(ConversationContext);
  if (!context) {
    throw new Error(
      "useConversation must be used within a ConversationProvider",
    );
  }
  return context;
}