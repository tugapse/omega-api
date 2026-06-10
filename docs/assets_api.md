# Assets API Documentation

This document provides a detailed guide for interacting with the Assets API.

**Base Path:** `/api/v1`

**Authentication:** All endpoints require a valid authentication token to be sent in the request headers.

---

## Endpoints

### 1. Get Project Asset Index

Retrieves a filtered and aggregated list of asset metadata for a specific project.

-   **Method:** `GET`
-   **Path:** `/projects/{project_id}/assets`
-   **URL Parameters:**
    -   `project_id` (string, required): The ID of the project.
-   **Query Parameters:**
    -   `type` (string, optional): Filter assets by type (e.g., "image", "audio", "code").
    -   `dir` (string, optional): Filter assets by a virtual directory prefix.
-   **Success Response (200 OK):**
    ```json
    {
      "project_id": "string",
      "total_assets": "integer",
      "total_size_bytes": "integer",
      "assets": [
        {
          "id": "string",
          "project_id": "string",
          "filename": "string",
          "virtual_path": "string",
          "asset_type": "string",
          "mime_type": "string",
          "size_bytes": "integer",
          "sha256": "string",
          "created_at": "string (ISO 8601)",
          "updated_at": "string (ISO 8601)"
        }
      ]
    }
    ```
-   **Error Responses:**
    -   `404 Not Found`: If the project does not exist or the user does not have access.

---

### 2. Upload a New Asset

Uploads a new asset to a project.

-   **Method:** `POST`
-   **Path:** `/projects/{project_id}/assets`
-   **URL Parameters:**
    -   `project_id` (string, required): The ID of the project.
-   **Request Body:** `multipart/form-data`
    -   `file` (file, required): The asset file to upload.
    -   `virtual_path` (string, optional): The desired logical path for the asset. If omitted, the filename is used.
    -   `asset_type` (string, optional): Manually override the detected asset type.
-   **Success Response (201 Created):**
    ```json
    {
      "id": "string",
      "project_id": "string",
      "filename": "string",
      "virtual_path": "string",
      "asset_type": "string",
      "mime_type": "string",
      "size_bytes": "integer",
      "sha256": "string",
      "created_at": "string (ISO 8601)",
      "updated_at": "string (ISO 8601)"
    }
    ```
-   **Error Responses:**
    -   `400 Bad Request`: If directory traversal characters are used in `virtual_path`.
    -   `404 Not Found`: If the project does not exist.
    -   `409 Conflict`: If an asset already exists at the specified `virtual_path`.
    -   `500 Internal Server Error`: If the file fails to write to disk.

---

### 3. Update or Move an Asset

Updates an asset's metadata or physically relocates it.

-   **Method:** `PATCH`
-   **Path:** `/projects/{project_id}/assets/{asset_id}`
-   **URL Parameters:**
    -   `project_id` (string, required): The ID of the project.
    -   `asset_id` (string, required): The ID of the asset to update.
-   **Request Body:** `application/json`
    ```json
    {
      "virtual_path": "string (optional)",
      "asset_type": "string (optional)"
    }
    ```
-   **Success Response (200 OK):** Returns the updated `AssetResponse` object.
-   **Error Responses:**
    -   `400 Bad Request`: If directory traversal characters are used in `virtual_path`.
    -   `404 Not Found`: If the project or asset does not exist.
    -   `409 Conflict`: If an asset already exists at the target `virtual_path`.

---

### 4. Delete an Asset

Deletes an asset's physical file and its database record.

-   **Method:** `DELETE`
-   **Path:** `/projects/{project_id}/assets/{asset_id}`
-   **URL Parameters:**
    -   `project_id` (string, required): The ID of the project.
    -   `asset_id` (string, required): The ID of the asset to delete.
-   **Success Response (200 OK):**
    ```json
    {
      "status": "success",
      "message": "Asset successfully unlinked and purged from server storage disk."
    }
    ```
-   **Error Responses:**
    -   `404 Not Found`: If the project or asset does not exist.

---

### 5. Stream Raw Asset Data

Serves the raw binary contents of a specific asset file.

-   **Method:** `GET`
-   **Path:** `/projects/{project_id}/assets/{asset_id}/raw`
-   **URL Parameters:**
    -   `project_id` (string, required): The ID of the project.
    -   `asset_id` (string, required): The ID of the asset to stream.
-   **Success Response (200 OK):**
    -   The raw binary data of the file with appropriate `Content-Type` and `Content-Length` headers.
-   **Error Responses:**
    -   `400 Bad Request`: If the asset path is invalid or insecure.
    -   `404 Not Found`: If the project, asset, or physical file does not exist.