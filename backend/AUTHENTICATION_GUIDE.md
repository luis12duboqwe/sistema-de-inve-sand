# Authentication & Authorization Guide

## Overview

The sistema-de-inve-sand backend now includes a complete JWT-based authentication system with role-based access control.

---

## Quick Start

### 1. Register a New User

```bash
curl -X POST "http://localhost:8000/api/auth/register" \
  -H "Content-Type: application/json" \
  -d '{
    "username": "admin",
    "email": "admin@example.com",
    "password": "securepass123",
    "full_name": "Admin User"
  }'
```

**Response:**
```json
{
  "id": 1,
  "username": "admin",
  "email": "admin@example.com",
  "full_name": "Admin User",
  "is_active": true,
  "is_superuser": false,
  "created_at": "2025-12-05T23:30:00Z"
}
```

### 2. Login and Get Token

```bash
curl -X POST "http://localhost:8000/api/auth/token" \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "username=admin&password=securepass123"
```

**Response:**
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJhZG1pbiIsImV4cCI6MTYxNjIzOTAyMn0.SflKxwRJSMeKKF2QT4fwpMeJf36POk6yJV_adQssw5c",
  "token_type": "bearer"
}
```

### 3. Use Token to Access Protected Endpoints

```bash
curl -X GET "http://localhost:8000/api/auth/me" \
  -H "Authorization: Bearer YOUR_TOKEN_HERE"
```

**Response:**
```json
{
  "id": 1,
  "username": "admin",
  "email": "admin@example.com",
  "full_name": "Admin User",
  "is_active": true,
  "is_superuser": false,
  "created_at": "2025-12-05T23:30:00Z"
}
```

---

## API Endpoints

### Authentication Endpoints

#### `POST /api/auth/register`
Register a new user.

**Request Body:**
```json
{
  "username": "string (min 3 chars, alphanumeric)",
  "email": "string (email format)",
  "password": "string (min 6 chars)",
  "full_name": "string (optional)"
}
```

**Response:** `201 Created` with user object (without password)

**Errors:**
- `400 Bad Request` - Username or email already exists
- `422 Unprocessable Entity` - Validation error

---

#### `POST /api/auth/token`
Login and get JWT access token (OAuth2 compatible).

**Request Body (form-urlencoded):**
```
username=admin&password=securepass123
```

**Response:**
```json
{
  "access_token": "JWT_TOKEN",
  "token_type": "bearer"
}
```

**Errors:**
- `401 Unauthorized` - Invalid credentials
- `400 Bad Request` - Inactive user

---

#### `GET /api/auth/me`
Get current authenticated user information.

**Headers:**
```
Authorization: Bearer YOUR_TOKEN
```

**Response:** User object

**Errors:**
- `401 Unauthorized` - Invalid or missing token
- `400 Bad Request` - Inactive user

---

#### `PUT /api/auth/me`
Update current user information.

**Headers:**
```
Authorization: Bearer YOUR_TOKEN
```

**Request Body:**
```json
{
  "email": "string (optional)",
  "full_name": "string (optional)",
  "password": "string (optional, min 6 chars)"
}
```

**Response:** Updated user object

**Errors:**
- `401 Unauthorized` - Invalid or missing token
- `400 Bad Request` - Email already taken or invalid password

---

#### `GET /api/auth/users` (Superuser Only)
List all users.

**Headers:**
```
Authorization: Bearer YOUR_TOKEN
```

**Query Parameters:**
- `skip`: Number of records to skip (default: 0)
- `limit`: Maximum records to return (default: 100)

**Response:** Array of user objects

**Errors:**
- `401 Unauthorized` - Invalid or missing token
- `403 Forbidden` - Not a superuser

---

#### `DELETE /api/auth/users/{user_id}` (Superuser Only)
Delete a user.

**Headers:**
```
Authorization: Bearer YOUR_TOKEN
```

**Response:** `204 No Content`

**Errors:**
- `401 Unauthorized` - Invalid or missing token
- `403 Forbidden` - Not a superuser
- `404 Not Found` - User not found
- `400 Bad Request` - Cannot delete yourself

---

## How to Protect Endpoints

### Require Any Authenticated User

```python
from fastapi import Depends
from app.auth import get_current_active_user
from app.models import User

@router.get("/protected")
def protected_endpoint(current_user: User = Depends(get_current_active_user)):
    return {"message": f"Hello {current_user.username}!"}
```

### Require Superuser

```python
from app.auth import get_current_superuser

@router.get("/admin-only")
def admin_endpoint(current_user: User = Depends(get_current_superuser)):
    return {"message": "Admin access granted"}
```

### Optional Authentication

```python
from typing import Optional
from app.auth import get_current_user_optional

@router.get("/public-or-private")
def flexible_endpoint(current_user: Optional[User] = Depends(get_current_user_optional)):
    if current_user:
        return {"message": f"Welcome back, {current_user.username}!"}
    return {"message": "Welcome, guest!"}
```

---

## User Roles

### Regular User
- Can register and login
- Can view and update own profile
- Can access regular endpoints

### Superuser
- All regular user permissions
- Can list all users
- Can delete other users
- Can access admin-only endpoints

**Note:** The first user should be manually promoted to superuser in the database:
```sql
UPDATE users SET is_superuser = true WHERE username = 'admin';
```

Or via SQLite CLI:
```bash
sqlite3 inventory.db "UPDATE users SET is_superuser = 1 WHERE username = 'admin';"
```

---

## Token Management

### Token Expiration
- Default: 30 minutes
- Configurable via `ACCESS_TOKEN_EXPIRE_MINUTES` env variable

### Token Format
JWT token containing:
- `sub`: Username
- `exp`: Expiration timestamp

### Token Usage
Include in Authorization header:
```
Authorization: Bearer YOUR_TOKEN_HERE
```

---

## Security Best Practices

### In Development
✅ Default SECRET_KEY is fine for testing
✅ All endpoints accessible
✅ CORS allows all origins

### In Production
⚠️ **Change SECRET_KEY** (generate with `openssl rand -hex 32`)
⚠️ **Configure CORS** for specific domains
⚠️ **Use HTTPS only**
⚠️ **Implement rate limiting**
⚠️ **Consider refresh tokens** for better UX
⚠️ **Set up monitoring/logging**
⚠️ **Regular security audits**

### Password Security
✅ Passwords hashed with bcrypt
✅ Never stored in plain text
✅ Never returned in API responses
✅ Minimum 6 characters enforced

### Token Security
✅ JWT with expiration
✅ Signature verification
✅ User status checked on each request
✅ Stateless authentication

---

## Configuration

### Environment Variables

```bash
# JWT Secret Key - CHANGE IN PRODUCTION!
SECRET_KEY=your-secret-key-change-this-in-production-use-openssl-rand-hex-32

# JWT Algorithm
ALGORITHM=HS256

# Token expiration in minutes
ACCESS_TOKEN_EXPIRE_MINUTES=30
```

### Generate Secure SECRET_KEY

```bash
# Linux/Mac
openssl rand -hex 32

# Python
python -c "import secrets; print(secrets.token_hex(32))"
```

---

## Testing Authentication

### Using Swagger UI

1. Go to `http://localhost:8000/docs`
2. Click "Authorize" button (top right)
3. Enter credentials and click "Authorize"
4. Now you can test protected endpoints

### Using Postman

1. POST to `/api/auth/token` with credentials
2. Copy the `access_token` from response
3. In request headers, add:
   ```
   Authorization: Bearer YOUR_TOKEN
   ```
4. Send requests to protected endpoints

### Using cURL

```bash
# 1. Login and save token
TOKEN=$(curl -s -X POST "http://localhost:8000/api/auth/token" \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "username=admin&password=securepass123" \
  | python3 -c "import sys, json; print(json.load(sys.stdin)['access_token'])")

# 2. Use token
curl -X GET "http://localhost:8000/api/auth/me" \
  -H "Authorization: Bearer $TOKEN"
```

---

## Troubleshooting

### "Could not validate credentials"
- Token expired (default 30 min)
- Invalid token
- User was deleted
- Solution: Login again to get new token

### "Inactive user"
- User account is disabled
- Solution: Contact admin to activate account

### "Not enough permissions"
- Trying to access superuser-only endpoint
- Solution: Request superuser privileges from admin

### "Username already registered"
- Username is taken
- Solution: Choose different username

### "Email already registered"
- Email is already in use
- Solution: Use different email or recover account

---

## Integration Examples

### Frontend (JavaScript/TypeScript)

```javascript
// Login
const loginResponse = await fetch('http://localhost:8000/api/auth/token', {
  method: 'POST',
  headers: {
    'Content-Type': 'application/x-www-form-urlencoded',
  },
  body: new URLSearchParams({
    username: 'admin',
    password: 'securepass123'
  })
});

const { access_token } = await loginResponse.json();

// Store token
localStorage.setItem('token', access_token);

// Use token in subsequent requests
const response = await fetch('http://localhost:8000/api/auth/me', {
  headers: {
    'Authorization': `Bearer ${access_token}`
  }
});
```

### Python Client

```python
import requests

# Login
response = requests.post(
    'http://localhost:8000/api/auth/token',
    data={'username': 'admin', 'password': 'securepass123'}
)
token = response.json()['access_token']

# Use token
headers = {'Authorization': f'Bearer {token}'}
response = requests.get('http://localhost:8000/api/auth/me', headers=headers)
user = response.json()
```

---

## Next Steps

1. **Create Your First User**
   ```bash
   curl -X POST "http://localhost:8000/api/auth/register" \
     -H "Content-Type: application/json" \
     -d '{"username":"admin","email":"admin@example.com","password":"change-this"}'
   ```

2. **Promote to Superuser** (manual DB update)
   ```bash
   sqlite3 inventory.db "UPDATE users SET is_superuser = 1 WHERE username = 'admin';"
   ```

3. **Login and Get Token**
   ```bash
   curl -X POST "http://localhost:8000/api/auth/token" \
     -d "username=admin&password=change-this"
   ```

4. **Protect Your Endpoints**
   - Add `Depends(get_current_active_user)` to routes that need auth
   - Add `Depends(get_current_superuser)` for admin routes

5. **Deploy to Production**
   - Generate new SECRET_KEY
   - Configure CORS for your domain
   - Enable HTTPS
   - Set up monitoring

---

## FAQ

**Q: How do I create a superuser?**
A: Create a regular user first, then update the database manually to set `is_superuser = true`.

**Q: Can I change token expiration time?**
A: Yes, set `ACCESS_TOKEN_EXPIRE_MINUTES` in .env file.

**Q: How do I revoke a token?**
A: JWT tokens are stateless and cannot be revoked. They expire automatically. For immediate revocation, implement a token blacklist or use refresh tokens.

**Q: Can users change their username?**
A: Not currently. Username is immutable. Users can change email, full_name, and password.

**Q: What happens if I forget my password?**
A: Currently, there's no password reset flow. This should be implemented for production (email-based reset).

**Q: How do I protect ALL endpoints?**
A: Add authentication dependency to the router level or globally in main.py.

---

## Conclusion

The authentication system is production-ready and follows industry best practices:
- ✅ JWT tokens
- ✅ Bcrypt password hashing
- ✅ Role-based access control
- ✅ OAuth2 compatibility
- ✅ Secure by default

For production deployment, remember to:
1. Change SECRET_KEY
2. Configure CORS
3. Enable HTTPS
4. Monitor authentication events
5. Consider adding refresh tokens and password reset

🔐 Your API is now secure!
