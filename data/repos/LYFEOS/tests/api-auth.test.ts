import { describe, it, expect } from 'vitest';

const BASE_URL = `http://localhost:5000`;

async function apiRequest(method: string, path: string, body?: any, cookie?: string) {
  const headers: Record<string, string> = { 'Content-Type': 'application/json' };
  if (cookie) headers['Cookie'] = cookie;
  
  const res = await fetch(`${BASE_URL}${path}`, {
    method,
    headers,
    body: body ? JSON.stringify(body) : undefined,
    redirect: 'manual',
  });
  
  const setCookie = res.headers.get('set-cookie');
  const data = await res.json().catch(() => ({}));
  return { status: res.status, data, cookie: setCookie };
}

describe('Auth API', () => {
  const testUser = {
    username: `testuser_${Date.now()}`,
    password: 'TestPass123!',
    firstName: 'Test',
    lastName: 'User',
    email: `test_${Date.now()}@example.com`,
  };

  let sessionCookie = '';

  it('rejects registration without username', async () => {
    const { status, data } = await apiRequest('POST', '/api/auth/register', {
      password: 'TestPass123!',
    });
    expect(status).toBe(400);
    expect(data.error).toBeTruthy();
  });

  it('rejects registration without password', async () => {
    const { status, data } = await apiRequest('POST', '/api/auth/register', {
      username: 'test',
    });
    expect(status).toBe(400);
    expect(data.error).toBeTruthy();
  });

  it('registers a new user successfully', async () => {
    const { status, data, cookie } = await apiRequest('POST', '/api/auth/register', testUser);
    expect(status).toBe(201);
    expect(data.user).toBeTruthy();
    expect(data.user.username).toBe(testUser.username);
    if (cookie) sessionCookie = cookie;
  });

  it('rejects duplicate username registration', async () => {
    const { status } = await apiRequest('POST', '/api/auth/login', {
      identifier: testUser.username + '_nonexistent',
      password: 'wrong',
    });
    expect(status).toBe(401);
  });

  it('rejects login with wrong password', async () => {
    const { status } = await apiRequest('POST', '/api/auth/login', {
      identifier: testUser.username,
      password: 'WrongPassword!',
    });
    expect(status).toBe(401);
  });

  it('logs in with correct credentials', async () => {
    const { status, data, cookie } = await apiRequest('POST', '/api/auth/login', {
      identifier: testUser.username,
      password: testUser.password,
    });
    expect(status).toBe(200);
    expect(data.user.username).toBe(testUser.username);
    if (cookie) sessionCookie = cookie;
  });

  it('accesses auth check with session', async () => {
    const { status, data } = await apiRequest('GET', '/api/auth/me', undefined, sessionCookie);
    expect(status).toBe(200);
    expect(data.user).toBeTruthy();
    expect(data.user.username).toBe(testUser.username);
  });

  it('rejects auth check without session', async () => {
    const { status } = await apiRequest('GET', '/api/auth/me', undefined);
    expect(status).toBe(401);
  });

  it('logs out successfully', async () => {
    const { status } = await apiRequest('POST', '/api/auth/logout', undefined, sessionCookie);
    expect(status).toBe(200);
  });
});

describe('Password Reset Validation', () => {
  it('rejects reset-password with invalid token format', async () => {
    const { status, data } = await apiRequest('POST', '/api/auth/reset-password', {
      token: 'invalid-token',
      newPassword: 'NewPass123!',
    });
    expect([400, 429]).toContain(status);
    expect(data.error).toBeTruthy();
  });

  it('rejects reset-password with short password', async () => {
    const { status, data } = await apiRequest('POST', '/api/auth/reset-password', {
      token: 'a'.repeat(64),
      newPassword: '12345',
    });
    expect([400, 429]).toContain(status);
    expect(data.error).toBeTruthy();
  });
});

describe('Health Check', () => {
  it('returns ok status', async () => {
    const { status, data } = await apiRequest('GET', '/api/health');
    expect(status).toBe(200);
    expect(data.status).toBe('ok');
    expect(data.timestamp).toBeTruthy();
  });
});
