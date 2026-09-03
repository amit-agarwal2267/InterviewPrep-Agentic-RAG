import { ChatPage } from "@/components/chat/ChatPage";

export default async function ConversationPage({
  params,
}: {
  params: Promise<{ conversation_id: string }>;
}) {
  const { conversation_id } = await params;
  return <ChatPage initialConversationId={conversation_id} />;
}
