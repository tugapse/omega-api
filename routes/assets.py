import os
import shutil
from datetime import datetime, timezone

import uuid
import hashlib
import mimetypes

from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Form
from starlette.responses import StreamingResponse
from typing import List, Optional
from tinydb import Query

from database import get_db
from schemas import (
    AssetResponse,
    ProjectAssetIndexResponse,
    UserResponse,
    AssetUpdateRequest,
)
from auth import get_current_user
from config import settings, resolve_path


router = APIRouter(
    tags=["Assets"],
)


@router.get(
    "/projects/{project_id}/assets",
    response_model=ProjectAssetIndexResponse,
    summary="Get a project's asset index",
)
def get_project_asset_index(
    project_id: str,
    type: Optional[str] = None,
    dir: Optional[str] = None,
    db=Depends(get_db),
    current_user: UserResponse = Depends(get_current_user),
):
    """
    Retrieves a filtered and aggregated list of asset metadata for a specific project.

    - **Security:** Requires user authentication and ownership of the project.
    - **Filtering:** Allows optional filtering by asset type and virtual directory prefix.
    """
    # 1. Verify project exists and belongs to the current user
    Project = Query()
    project_table = db.table("projects")
    project = project_table.get((Project.id == project_id) & (Project.owner_id == current_user["id"]))

    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project not found",
        )

    # 2. Query assets for the given project_id
    Asset = Query()
    asset_table = db.table("assets")
    all_project_assets = asset_table.search(Asset.project_id == project_id)

    # 3. Apply optional filters
    filtered_assets = []
    for asset_doc in all_project_assets:
        # Type filtering
        if type and asset_doc.get("asset_type") != type:
            continue
        # Directory filtering
        if dir and not asset_doc.get("virtual_path", "").startswith(dir):
            continue
        filtered_assets.append(asset_doc)

    # 4. Prepare response models and calculate aggregates
    asset_responses = [AssetResponse(**asset) for asset in filtered_assets]
    total_size_bytes = sum(asset.size_bytes for asset in asset_responses)
    total_assets = len(asset_responses)

    # 5. Return the structured response
    return ProjectAssetIndexResponse(
        project_id=project_id,
        total_assets=total_assets,
        total_size_bytes=total_size_bytes,
        assets=asset_responses,
    )


@router.post(
    "/projects/{project_id}/assets",
    response_model=AssetResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Upload a new asset",
)
async def create_asset(
    project_id: str,
    file: UploadFile = File(...),
    virtual_path: Optional[str] = Form(None),
    asset_type: Optional[str] = Form(None),
    db=Depends(get_db),
    current_user: UserResponse = Depends(get_current_user),
):
    """
    Uploads a new asset to a project, fingerprints it, and registers it in the database.

    - **Security:** Requires user authentication and ownership of the project.
    - **Performance:** Streams uploads to disk and calculates SHA256 on the fly.
    - **Metadata:**
        - `virtual_path`: The desired logical path. If omitted, the filename is used.
        - `asset_type`: Manually override the detected asset type.
    """
    # 1. Verify project exists and belongs to the current user
    Project = Query()
    project_table = db.table("projects")
    project = project_table.get((Project.id == project_id) & (Project.owner_id == current_user["id"]))

    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project not found",
        )

    # 2. Sanitize and determine virtual path
    if virtual_path:
        if "../" in virtual_path or "..\\" in virtual_path:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Directory traversal characters (../) are strictly prohibited.",
            )
        final_virtual_path = virtual_path.lstrip("/")
    else:
        final_virtual_path = file.filename

    # 3. Collision Detection
    Asset = Query()
    asset_table = db.table("assets")
    if asset_table.get((Asset.project_id == project_id) & (Asset.virtual_path == final_virtual_path)):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"An asset already exists at path: {final_virtual_path}",
        )

    # 4. Physical Storage and Fingerprinting
    base_path_str = f"@ROOT/storage/{current_user['id']}/projects/{project_id}"
    physical_path = resolve_path(f"{base_path_str}/{final_virtual_path}")
    
    os.makedirs(os.path.dirname(physical_path), exist_ok=True)

    sha256_hash = hashlib.sha256()
    size_bytes = 0
    
    try:
        with open(physical_path, "wb") as f:
            while content := await file.read(65536):  # 64KB chunks
                sha256_hash.update(content)
                f.write(content)
                size_bytes += len(content)
    except Exception as e:
        # Cleanup partial file on error
        if os.path.exists(physical_path):
            os.remove(physical_path)
        raise HTTPException(status_code=500, detail=f"Failed to write file to disk: {e}")

    # 5. Metadata Finalization
    now_iso = datetime.now(timezone.utc).isoformat() + "Z"
    mime_type, _ = mimetypes.guess_type(physical_path)
    
    final_asset_type = asset_type
    if not final_asset_type:
        if mime_type:
            if mime_type.startswith("image/"):
                final_asset_type = "image"
            elif mime_type.startswith("audio/"):
                final_asset_type = "audio"
            elif mime_type.startswith("text/") or mime_type in ["application/javascript", "application/x-python-code"]:
                final_asset_type = "code"
            elif mime_type.startswith("text/plain"):
                final_asset_type = "text"
            else:
                final_asset_type = "raw"
        else:
            final_asset_type = "raw"

    # 6. Database Registration
    new_asset_doc = {
        "id": str(uuid.uuid4()),
        "project_id": project_id,
        "filename": os.path.basename(final_virtual_path),
        "virtual_path": final_virtual_path,
        "asset_type": final_asset_type,
        "mime_type": mime_type or "application/octet-stream",
        "size_bytes": size_bytes,
        "sha256": sha256_hash.hexdigest(),
        "created_at": now_iso,
        "updated_at": now_iso,
    }

    asset_table.insert(new_asset_doc)
    
    return AssetResponse(**new_asset_doc)


@router.patch(
    "/projects/{project_id}/assets/{asset_id}",
    response_model=AssetResponse,
    summary="Update or move an asset",
)
def update_asset(
    project_id: str,
    asset_id: str,
    update_data: AssetUpdateRequest,
    db=Depends(get_db),
    current_user: UserResponse = Depends(get_current_user),
):
    """
    Updates an asset's metadata or physically relocates it within the project's storage.

    - **Security:** Requires user authentication and ownership of the project.
    - **Operations:**
        - Modify `asset_type`.
        - Rename/move asset by changing `virtual_path`.
    """
    # 1. Verify project exists and belongs to the current user
    Project = Query()
    project_table = db.table("projects")
    project = project_table.get((Project.id == project_id) & (Project.owner_id == current_user["id"]))

    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project not found",
        )

    # 2. Asset Node Verification
    Asset = Query()
    asset_table = db.table("assets")
    asset_doc = asset_table.get((Asset.id == asset_id) & (Asset.project_id == project_id))

    if not asset_doc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Asset not found",
        )

    update_payload = update_data.dict(exclude_unset=True)
    
    # 3. Path Sanitization and Collision Interception
    if "virtual_path" in update_payload and update_payload["virtual_path"] is not None:
        new_virtual_path = update_payload["virtual_path"]
        
        if "../" in new_virtual_path or "..\\" in new_virtual_path:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Directory traversal characters (../) are strictly prohibited.",
            )
        
        new_virtual_path = new_virtual_path.lstrip("/")
        update_payload["virtual_path"] = new_virtual_path

        # Collision Detection
        existing_asset = asset_table.get(
            (Asset.project_id == project_id) &
            (Asset.virtual_path == new_virtual_path) &
            (Asset.id != asset_id)
        )
        if existing_asset:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="An asset already exists at the target destination path.",
            )

        # 4. Physical File System Moving Engine
        old_virtual_path = asset_doc["virtual_path"]
        
        if new_virtual_path != old_virtual_path:
            base_path_str = f"@ROOT/storage/{current_user['id']}/projects/{project_id}"
            
            source_absolute_path = resolve_path(f"{base_path_str}/{old_virtual_path}")
            destination_absolute_path = resolve_path(f"{base_path_str}/{new_virtual_path}")

            destination_dir = os.path.dirname(destination_absolute_path)
            os.makedirs(destination_dir, exist_ok=True)

            if not os.path.exists(source_absolute_path):
                 raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Source file not found at {old_virtual_path}. Cannot perform move.",
                )
            shutil.move(source_absolute_path, destination_absolute_path)

            old_parent_dir = os.path.dirname(source_absolute_path)
            if os.path.isdir(old_parent_dir) and not os.listdir(old_parent_dir):
                try:
                    os.removedirs(old_parent_dir)
                except OSError:
                    pass
        
        update_payload["filename"] = os.path.basename(new_virtual_path)

    # 5. Index Entry Synchronization
    if update_payload:
        update_payload["updated_at"] = datetime.now(timezone.utc).isoformat() + "Z"
        asset_table.update(update_payload, doc_ids=[asset_doc.doc_id])
    else:
        return AssetResponse(**asset_doc)

    updated_asset_doc = asset_table.get(doc_id=asset_doc.doc_id)
    return AssetResponse(**updated_asset_doc)


@router.delete(
    "/projects/{project_id}/assets/{asset_id}",
    status_code=status.HTTP_200_OK,
    summary="Delete an asset",
)
def delete_asset(
    project_id: str,
    asset_id: str,
    db=Depends(get_db),
    current_user: UserResponse = Depends(get_current_user),
):
    """
    Deletes an asset, including its physical file and database record.

    - **Security:** Requires user authentication and ownership of the project.
    - **Synchronicity:** Deletes the file from disk and the record from the database.
    - **Cleanup:** Removes empty parent directories after file deletion.
    """
    # 1. Verify project exists and belongs to the current user
    Project = Query()
    project_table = db.table("projects")
    project = project_table.get((Project.id == project_id) & (Project.owner_id == current_user["id"]))

    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project not found",
        )

    # 2. Asset Registry Verification
    Asset = Query()
    asset_table = db.table("assets")
    asset_doc = asset_table.get((Asset.id == asset_id) & (Asset.project_id == project_id))

    if not asset_doc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Asset not found",
        )

    # 3. Physical File Erasure Engine
    virtual_path = asset_doc["virtual_path"]
    base_path_str = f"@ROOT/storage/{current_user['id']}/projects/{project_id}"
    absolute_path = resolve_path(f"{base_path_str}/{virtual_path}")

    if os.path.exists(absolute_path):
        os.remove(absolute_path)
        
        parent_dir = os.path.dirname(absolute_path)
        # Check if the directory is a directory and if it's empty.
        if os.path.isdir(parent_dir) and not os.listdir(parent_dir):
            try:
                # Recursively remove empty directories
                os.removedirs(parent_dir)
            except OSError:
                # This can happen if the directory becomes non-empty
                # between the check and the removal (race condition)
                # or if permissions are insufficient.
                # We can safely ignore it.
                pass
    
    # 4. Database Cleansing Sync
    asset_table.remove(doc_ids=[asset_doc.doc_id])

    return {
        "status": "success",
        "message": "Asset successfully unlinked and purged from server storage disk."
    }


def chunked_file_reader(file_path: str, chunk_size: int = 65536):
    """Generator to read a file in chunks."""
    with open(file_path, "rb") as f:
        while True:
            chunk = f.read(chunk_size)
            if not chunk:
                break
            yield chunk


@router.get(
    "/projects/{project_id}/assets/{asset_id}/raw",
    response_class=StreamingResponse,
    summary="Stream raw asset binary data",
)
def stream_raw_asset(
    project_id: str,
    asset_id: str,
    db=Depends(get_db),
    current_user: UserResponse = Depends(get_current_user),
):
    """
    Serves the raw binary contents of a specific asset file.

    - **Security:** Requires user authentication and ownership of the project.
    - **Performance:** Streams the file in chunks to minimize memory usage.
    - **Headers:** Sets `Content-Type` and `Content-Length` from database metadata.
    """
    # 1. Identity Validation & Project Bounds
    Project = Query()
    project_table = db.table("projects")
    project = project_table.get((Project.id == project_id) & (Project.owner_id == current_user["id"]))

    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project not found",
        )

    # 2. Asset Node Verification
    Asset = Query()
    asset_table = db.table("assets")
    asset_doc = asset_table.get((Asset.id == asset_id) & (Asset.project_id == project_id))

    if not asset_doc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Asset not found",
        )

    # 3. Path Resolution & Sanitization Guardrails
    virtual_path = asset_doc.get("virtual_path")
    if not virtual_path or "../" in virtual_path or "..\\" in virtual_path:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or insecure asset path.",
        )

    physical_path_str = f"@ROOT/storage/{current_user['id']}/projects/{project_id}/{virtual_path}"
    physical_path = resolve_path(physical_path_str)

    if not os.path.exists(physical_path):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Physical asset file missing from server storage disk",
        )

    # 4. Asynchronous Streaming Delivery Engine
    file_generator = chunked_file_reader(physical_path)
    
    media_type = asset_doc.get("mime_type", "application/octet-stream")
    content_length = str(asset_doc.get("size_bytes", 0))

    headers = {
        "Content-Length": content_length,
    }

    return StreamingResponse(
        content=file_generator,
        media_type=media_type,
        headers=headers,
    )