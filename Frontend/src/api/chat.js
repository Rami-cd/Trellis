import { client } from './client';

function getToken() {
  return localStorage.getItem('token');
}

async function createConversation(repoId) {
  const response = await client.post(`/repositories/${repoId}/conversations`);
  return response.data.conversation_id;
}

async function streamChatResponse(response, onChunk) {
  if (!response.ok) {
    const errorText = await response.text();
    throw new Error(errorText || `Request failed with status ${response.status}`);
  }

  if (!response.body) {
    throw new Error('Streaming response body is not available');
  }

  const reader = response.body.getReader();
  const decoder = new TextDecoder();

  try {
    while (true) {
      const { done, value } = await reader.read();
      if (done) {
        break;
      }

      const chunk = decoder.decode(value, { stream: true });
      if (chunk) {
        onChunk(chunk);
      }
    }

    const tail = decoder.decode();
    if (tail) {
      onChunk(tail);
    }
  } finally {
    reader.releaseLock();
  }
}

async function sendMessage(repoId, message, conversationId, onChunk) {
  const finalConversationId = conversationId ?? await createConversation(repoId);
  const token = getToken();

  const response = await fetch(`${import.meta.env.VITE_API_URL}/repositories/${repoId}/chat`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      ...(token
        ? {
            Authorization: `Bearer ${token}`,
          }
        : {}),
    },
    body: JSON.stringify({
      message,
      conversation_id: finalConversationId,
      top_k: 5,
      depth: 2,
    }),
  });

  await streamChatResponse(response, onChunk);
  return finalConversationId;
}

export { sendMessage };
