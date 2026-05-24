# Omega API Documentation

This document provides a comprehensive and highly detailed map of the Omega API, specifically designed for client-side agents. It includes all exact paths, required schemas, request types, and crucial backend implementation details ("ins and outs") to prevent integration bugs.

## Base Configuration

- **API Prefix:** `/api/v1` (All routes except health check).
- **Base URL:** `http://<server-host>:5000` (e.g., `http://localhost:5000`).
- **CORS:** Configured to allow all methods/headers for `localhost:4200` and specific production/staging domains.

---

## Crucial Ins and Outs (Implementation Details)

To successfully implement the client, you **must** be aware of these backend quirks:

1. **Auto-Slugs:** When creating or patching a project, the backend automatically generates and updates the project's `slug` based on the `name`. The client does not need to compute or send a slug.
2. **Asset Virtual Paths:** `virtual_path` is sanitized (leading slashes are removed). Directory traversal (`../` or `..\`) is strictly rejected with a 400 error.
3. **Physical Asset Moving:** If you update an asset's `virtual_path` via `PATCH /api/v1/projects/{project_id}/assets/{asset_id}`, the backend physically moves the file on the storage disk and cleans up any empty parent directories.
4. **Asset Fingerprinting:** `sha256` and `size_bytes` are computed automatically by the backend via a disk stream upon upload. `asset_type` is also inferred automatically via MIME type unless explicitly provided by the client.

---

## 1. System Health

### `GET /health` (No Prefix)
- **Description:** Server health check.
- **Auth Required:** No
- **Response (200 OK):**
  ```json
  { "status": "healthy" }
  ```

---

## 2. Authentication & Users

### `POST /api/v1/auth/register`
- **Description:** Registers a new user.
- **Auth Required:** No
- **Content-Type:** `application/json`
- **Request Body:**
  ```json
  {
    "username": "string", // 3-30 chars, alphanumeric only (^[a-zA-Z0-9]+$)
    "email": "user@example.com", // Valid email address format
    "password": "string" // Minimum 6 characters
  }
  ```
- **Response (201 Created):** Returns a full `UserResponse` object.
- **Errors:** 400 if email or username already exists.

### `POST /api/v1/auth/login`
- **Description:** Logs in an existing user and retrieves a JWT access token.
- **Auth Required:** No
- **Content-Type:** `application/json`
- **Request Body:**
  ```json
  {
    "username": "string",
    "password": "strongpassword123"
  }
  ```
- **Response (200 OK):**
  ```json
  {
    "token": "jwt-token-string",
    "access_token": "jwt-token-string",
    "token_type": "bearer"
  }
  ```
- **Errors:** 401 if username does not exist.

### `POST /api/v1/auth/logout`
- **Description:** Logs out the user (client should clear the token).
- **Auth Required:** Yes
- **Response (200 OK):** `{"message": "Successfully logged out"}`

### `GET /api/v1/users/me`
- **Description:** Retrieves the authenticated user's profile.
- **Auth Required:** Yes
- **Response (200 OK):** `UserResponse` object.

### `PATCH /api/v1/users/me`
- **Description:** Updates the user's profile.
- **Auth Required:** Yes
- **Content-Type:** `application/json`
- **Request Body (Optional fields):**
  ```json
  {
    "username": "new_username",
    "email": "new@example.com"
  }
  ```
- **Response (200 OK):** Updated `UserResponse` object.

### `GET /api/v1/users/me/preferences`
- **Description:** Retrieves user preferences.
- **Auth Required:** Yes
- **Response (200 OK):** `UserPreferences` object.

### `PUT /api/v1/users/me/preferences`
- **Description:** Fully replaces the user's preferences.
- **Auth Required:** Yes
- **Content-Type:** `application/json`
- **Request Body:** `UserPreferences` object.
- **Response (200 OK):** Updated `UserPreferences` object.

---

## 3. Projects

*Requires Authentication header: `Authorization: Bearer <token>`*

### `POST /api/v1/projects`
- **Description:** Creates a new project.
- **Content-Type:** `application/json`
- **Request Body:**
  ```json
  {
    "name": "My Project", // Required: 1-100 characters
    "description": "Optional desc", // Optional: Max 500 chars
    "settings": { // Optional
      "environment": "development", // "development" | "staging" | "production" (Default: "development")
      "version": "1.0.0" // Regex ^\d+\.\d+\.\d+$ (Default: "1.0.0")
    }
  }
  ```
- **Response (201 Created):** `ProjectResponse` object.

### `GET /api/v1/projects`
- **Description:** Lists all projects owned by the user.
- **Response (200 OK):** Array of `ProjectResponse` objects.

### `GET /api/v1/projects/{project_id}`
- **Description:** Retrieves a specific project.
- **Path Parameter:** `project_id` (UUID string)
- **Response (200 OK):** `ProjectResponse` object.
- **Errors:** 404 if not found or unauthorized.

### `PATCH /api/v1/projects/{project_id}`
- **Description:** Partially updates project metadata.
- **Path Parameter:** `project_id` (UUID string)
- **Content-Type:** `application/json`
- **Request Body (All fields optional):**
  ```json
  {
    "name": "New Name",
    "description": "New description",
    "settings": {
      "environment": "production",
      "version": "1.1.0"
    }
  }
  ```
  *(Note: Updating `name` will trigger backend to auto-regenerate the `slug`.)*
- **Response (200 OK):** Updated `ProjectResponse` object.

### `DELETE /api/v1/projects/{project_id}`
- **Description:** Deletes a project and all associated assets.
- **Path Parameter:** `project_id` (UUID string)
- **Response (200 OK):**
  ```json
  {
    "status": "success",
    "message": "Project workspace and all associated physical assets purged from disk."
  }
  ```

---

## 4. Assets

*Requires Authentication header & user must own the project.*

### `GET /api/v1/projects/{project_id}/assets`
- **Description:** Get an index of the project's assets with aggregation (total counts and size).
- **Path Parameter:** `project_id` (UUID string)
- **Query Parameters:**
  - `type` (optional): "code" | "image" | "audio" | "text" | "raw"
  - `dir` (optional): Filters by `virtual_path` prefix.
- **Response (200 OK):** `ProjectAssetIndexResponse` object.

### `POST /api/v1/projects/{project_id}/assets`
- **Description:** Uploads a file.
- **Path Parameter:** `project_id` (UUID string)
- **Content-Type:** `multipart/form-data`
- **Request Payload:**
  - `file` (Binary File Blob, required)
  - `virtual_path` (Text, optional): The logical path (e.g., `src/main.js`). If omitted, uses the uploaded file's name.
  - `asset_type` (Text, optional): Explicit override. If omitted, backend infers it via MIME type.
- **Response (201 Created):** `AssetResponse` object.
- **Errors:** 409 Conflict if path already exists. 400 Bad Request if path contains `../`.

### `PATCH /api/v1/projects/{project_id}/assets/{asset_id}`
- **Description:** Updates asset metadata or relocates the file.
- **Path Parameters:** `project_id` (UUID string), `asset_id` (UUID string)
- **Content-Type:** `application/json`
- **Request Body (Optional fields):**
  ```json
  {
    "virtual_path": "new/path/to/file.png",
    "asset_type": "image" // "code" | "image" | "audio" | "text" | "raw"
  }
  ```
  *(Note: Updating `virtual_path` triggers a physical file move on disk. Old empty directories are automatically pruned.)*
- **Response (200 OK):** Updated `AssetResponse` object.

### `DELETE /api/v1/projects/{project_id}/assets/{asset_id}`
- **Description:** Deletes an asset from the DB and storage.
- **Path Parameters:** `project_id` (UUID string), `asset_id` (UUID string)
- **Response (200 OK):**
  ```json
  {
    "status": "success",
    "message": "Asset successfully unlinked and purged from server storage disk."
  }
  ```

### `GET /api/v1/projects/{project_id}/assets/{asset_id}/raw`
- **Description:** Streams the raw binary content of an asset.
- **Path Parameters:** `project_id` (UUID string), `asset_id` (UUID string)
- **Response (200 OK):** `StreamingResponse` with raw binary data. Response headers include the corresponding `Content-Type` and `Content-Length`.

---

## Detailed Data Models (Schemas)

### `UserPreferences`
```typescript
{
  theme: "dark" | "light"; // Default: "dark"
  notifications_enabled: boolean; // Default: true
  editor_settings: Record<string, string>; // Key-value pairs (Default: {})
}
```

### `UserResponse`
```typescript
{
  id: string; // UUID
  username: string;
  email: string;
  preferences: UserPreferences;
  created_at: string; // ISO-8601 string (e.g., "2023-01-01T12:00:00Z")
  updated_at: string; // ISO-8601 string
}
```

### `ProjectResponse`
```typescript
{
  id: string; // UUID
  slug: string; // Auto-generated string
  owner_id: string; // UUID
  name: string;
  description: string | null;
  status: "active" | "archived" | "maintenance";
  settings: {
    environment: "development" | "staging" | "production";
    version: string;
  };
  created_at: string; // ISO-8601 string
  updated_at: string; // ISO-8601 string
}
```

### `AssetResponse`
```typescript
{
  id: string; // UUID
  filename: string; // Just the file name portion of the virtual_path
  virtual_path: string; // Full logical path
  asset_type: "code" | "image" | "audio" | "text" | "raw";
  mime_type: string;
  size_bytes: number; // Automatically calculated
  sha256: string; // 64-character hash, automatically calculated
  created_at: string; // ISO-8601 string
  updated_at: string; // ISO-8601 string
}
```

### `ProjectAssetIndexResponse`
```typescript
{
  project_id: string; // UUID
  total_assets: number; // Total count matching filter
  total_size_bytes: number; // Total size of matching assets
  assets: AssetResponse[];
}
```