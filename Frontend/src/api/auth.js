import { client } from './client';

const register = async (email, password) => {
  try {
    const response = await client.post('/auth/register', {
      email,
      password,
    });
    return response.data;
  } catch (error) {
    throw error;
  }
}

const login = async (email, password) => {
  try {
    const params = new URLSearchParams();
    params.set('username', email);
    params.set('password', password);

    const response = await client.post('/auth/login', params, {
      headers: {
        'Content-Type': 'application/x-www-form-urlencoded',
      },
    });

    const token = response.data?.access_token;
    if (token) {
      localStorage.setItem('token', token);
    }

    return response.data;
  } catch (error) {
    throw error;
  }
}

export { register, login };