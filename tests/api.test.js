const request = require('supertest');
const app = require('../src/app');

describe('API smoke tests', () => {
  test('GET / returns welcome message', async () => {
    const res = await request(app).get('/');
    expect(res.statusCode).toBe(200);
    expect(res.body.message).toContain('Secure Password Manager API');
  });

  test('POST /api/auth/register requires username and password', async () => {
    const res = await request(app).post('/api/auth/register').send({});
    expect(res.statusCode).toBe(400);
    expect(res.body.error).toContain('username and password required');
  });

  test('POST /api/auth/login requires username and password', async () => {
    const res = await request(app).post('/api/auth/login').send({});
    expect(res.statusCode).toBe(400);
    expect(res.body.error).toContain('username and password required');
  });

  test('GET /api/entries without auth returns 401', async () => {
    const res = await request(app).get('/api/entries');
    expect(res.statusCode).toBe(401);
  });
});
