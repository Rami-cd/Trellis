import { client } from './client';

async function listConversations(repoId) {
  try {
    const response = await client.get(`/repositories/${repoId}/conversations`);
    return response.data;
  } catch (error) {
    throw error;
  }
}

async function getMessages(conversationId) {
  try {
    const response = await client.get(`/conversations/${conversationId}/messages`);
    return response.data;
  } catch (error) {
    throw error;
  }
}

export { listConversations, getMessages };
