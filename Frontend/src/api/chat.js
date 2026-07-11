import { client } from './client';

function getToken() {
  return localStorage.getItem('token');
}

async function createConversation(repoId) {
  const response = await client.post(`/repositories/${repoId}/conversations`);
  return response.data.conversation_id;
}

async function streamChatResponse(response, { onChunk, onGraph, onDone, onError }) {
  if (!response.ok) {
    const errorText = await response.text();
    throw new Error(errorText || `Request failed with status ${response.status}`);
  }

  if (!response.body) {
    throw new Error('Streaming response body is not available');
  }

  const reader = response.body.getReader();
  const decoder = new TextDecoder();
  let buffer = '';

  let graphReceived = false;
  let firstChunkReceived = false;

  const handleLine = (line) => {
    if (!line.trim()) return;
    let event;
    try {
      event = JSON.parse(line);
    } catch {
      return;
    }

    switch (event.type) {
      case 'text':
        if (!firstChunkReceived) {
          firstChunkReceived = true;
          console.log('[chat] first text chunk received. graph arrived first?', graphReceived);
        }
        onChunk?.(event.content);
        break;
      case 'graph':
        graphReceived = true;
        console.log('[chat] graph event received:', event);
        onGraph?.(event);
        break;
      case 'done':
        onDone?.(event);
        break;
      case 'error':
        onError?.(event.message);
        break;
      default:
        break;
    }
  };

  try {
    while (true) {
      const { done, value } = await reader.read();
      if (done) break;

      buffer += decoder.decode(value, { stream: true });
      const lines = buffer.split('\n');
      buffer = lines.pop(); // keep incomplete last line for next chunk

      for (const line of lines) {
        handleLine(line);
      }
    }

    buffer += decoder.decode();
    if (buffer.trim()) handleLine(buffer);
  } finally {
    reader.releaseLock();
  }
}

async function sendMessage(repoId, message, conversationId, callbacks) {
  const finalConversationId = conversationId ?? await createConversation(repoId);
  const token = getToken();
  const apiBaseUrl = import.meta.env.VITE_API_URL || 'http://localhost:8000';

  const response = await fetch(`${apiBaseUrl}/repositories/${repoId}/chat`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
    },
    body: JSON.stringify({
      message,
      conversation_id: finalConversationId,
      top_k: 5,
      depth: 2,
    }),
  });

  await streamChatResponse(response, callbacks);
  return finalConversationId;
}

export { sendMessage };