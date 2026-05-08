import { client } from './client';

async function uploadRepo(url) {
  try {
    const formData = new FormData();
    formData.append('url', url);

    const response = await client.post('/repositories/upload', formData);
    return response.data;
  } catch (error) {
    throw error;
  }
}

async function uploadRepoZip(file) {
  try {
    const formData = new FormData();
    formData.append('file', file);

    const response = await client.post('/repositories/upload', formData);
    return response.data;
  } catch (error) {
    throw error;
  }
}

async function listRepos() {
  try {
    const response = await client.get('/repositories/');
    return response.data;
  } catch (error) {
    throw error;
  }
}

async function getRepo(repoId) {
  try {
    const response = await client.get(`/repositories/${repoId}`);
    return response.data;
  } catch (error) {
    throw error;
  }
}

async function deleteRepo(repoId) {
  try {
    const response = await client.delete(`/repositories/${repoId}`);
    return response.data;
  } catch (error) {
    throw error;
  }
}

export { uploadRepo, uploadRepoZip, listRepos, getRepo, deleteRepo };
