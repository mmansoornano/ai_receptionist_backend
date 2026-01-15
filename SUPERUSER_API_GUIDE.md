# Superuser Creation API Endpoint

## Overview

The `/api/auth/create-superuser/` endpoint allows you to create a superuser (admin) account via API. This endpoint is **only accessible from the backend/localhost** for security reasons.

## Security

The endpoint has two layers of security:

1. **IP Restriction**: Only accepts requests from localhost (`127.0.0.1`, `::1`, or `localhost`)
2. **Optional Token**: If `SUPERUSER_CREATE_TOKEN` is set in `.env`, requests must include the token in the `X-Superuser-Token` header

## Endpoint

**POST** `/api/auth/create-superuser/`

## Request Headers

```
Content-Type: application/json
X-Superuser-Token: <token>  # Optional, only if SUPERUSER_CREATE_TOKEN is set in .env
```

## Request Body

```json
{
    "username": "admin",
    "email": "admin@example.com",
    "password": "secure_password_123",
    "first_name": "Admin",
    "last_name": "User"
}
```

### Required Fields
- `username`: String, minimum 3 characters, must be unique
- `email`: String, valid email format, must be unique
- `password`: String, minimum 8 characters

### Optional Fields
- `first_name`: String
- `last_name`: String

## Response

### Success (201 Created)

```json
{
    "success": true,
    "message": "Superuser created successfully",
    "user": {
        "id": 1,
        "username": "admin",
        "email": "admin@example.com",
        "is_staff": true,
        "is_superuser": true
    }
}
```

### Error Responses

#### 403 Forbidden (Not from localhost)
```json
{
    "success": false,
    "error": "Access denied. This endpoint is only accessible from the backend."
}
```

#### 400 Bad Request (Validation errors)
```json
{
    "success": false,
    "error": "Validation failed",
    "details": {
        "username": ["Username already exists"],
        "password": ["Password must be at least 8 characters"]
    }
}
```

## Usage Examples

### Using curl (from localhost)

```bash
# Basic request (no token required if SUPERUSER_CREATE_TOKEN is not set)
curl -X POST http://localhost:8000/api/auth/create-superuser/ \
  -H "Content-Type: application/json" \
  -d '{
    "username": "admin",
    "email": "admin@example.com",
    "password": "secure_password_123",
    "first_name": "Admin",
    "last_name": "User"
  }'
```

### Using curl with token (if SUPERUSER_CREATE_TOKEN is set)

```bash
curl -X POST http://localhost:8000/api/auth/create-superuser/ \
  -H "Content-Type: application/json" \
  -H "X-Superuser-Token: your-secret-token-here" \
  -d '{
    "username": "admin",
    "email": "admin@example.com",
    "password": "secure_password_123",
    "first_name": "Admin",
    "last_name": "User"
  }'
```

### Using Python requests

```python
import requests

url = "http://localhost:8000/api/auth/create-superuser/"
headers = {
    "Content-Type": "application/json"
}

# Optional: Add token if SUPERUSER_CREATE_TOKEN is set
# headers["X-Superuser-Token"] = "your-secret-token-here"

data = {
    "username": "admin",
    "email": "admin@example.com",
    "password": "secure_password_123",
    "first_name": "Admin",
    "last_name": "User"
}

response = requests.post(url, json=data, headers=headers)
print(response.json())
```

## Environment Variable (Optional)

Add to your `.env` file for additional security:

```bash
SUPERUSER_CREATE_TOKEN=your-secret-token-here
```

If this is set, all requests must include the token in the `X-Superuser-Token` header.

## Notes

- The endpoint only works from `localhost` or `127.0.0.1`
- The created user will have both `is_staff=True` and `is_superuser=True`
- Username and email must be unique
- Password must be at least 8 characters
- This endpoint is intended for backend/internal use only
