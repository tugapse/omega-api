# Authentication System Documentation

This document explains the authentication system implemented in the frontend, so that the server-side agent can adapt the backend to work seamlessly with it.

## Overview

The client now manages a JWT token directly instead of relying on the backend to set an `HttpOnly` cookie. When a user successfully authenticates, the server should return the JWT token in the response payload. The client then saves this token in a document cookie and attaches it as a `Bearer` token in the `Authorization` header on subsequent requests.

## Server-Side Requirements

### 1. Login Endpoint (`POST /auth/login`)
When a user provides valid credentials, the server **must** return the token in the JSON response body under the `token` property.

**Expected Response Payload:**
```json
{
  "token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
}
```

### 2. Validating Requests
The client uses an Angular `HttpInterceptor` (`AuthInterceptor`) that automatically appends the token to all outgoing API requests using the `Authorization` header.

**Incoming Request Header:**
```http
Authorization: Bearer <token_string_here>
```

The server needs to:
- Extract the token from the `Authorization` header.
- Verify its signature and expiration.
- If valid, allow the request to proceed.
- If invalid or missing (for protected endpoints), return a `401 Unauthorized` HTTP status. The client is programmed to clear the local session and redirect the user to the login page upon receiving a `401`.

### 3. Logout Endpoint (`POST /auth/logout`)
The client will send a POST request to this endpoint and will clear the local token cookie regardless of the server's response. The server can invalidate the token (if using a token blocklist or similar mechanism) but no longer needs to instruct the client to clear an `HttpOnly` cookie.

### 4. Registration Endpoint (`POST /auth/register`)
This endpoint functions as usual. If it is meant to automatically log the user in, it should also return the token in the payload just like the login endpoint. If it only creates the user, returning a `200 OK` or `201 Created` without a token is sufficient (the user will need to log in manually afterwards).

## Summary
- **No HttpOnly Cookies:** The server no longer needs to use `Set-Cookie` for auth credentials.
- **Client Cookie Service:** The client uses a custom `CookieService` to handle storing the `auth_token`.
- **Bearer Token Auth:** The server must look for `Authorization: Bearer <token>` on protected routes.