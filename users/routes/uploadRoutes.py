from fastapi import APIRouter, UploadFile, File, HTTPException
import os
import uuid
import shutil

router = APIRouter()

UPLOAD_DIR = "uploads/profiles"

@router.post("/user/upload-profile")
async def upload_image(file: UploadFile = File(...)):
    try:
        os.makedirs(UPLOAD_DIR, exist_ok=True)

        # ❌ DO NOT TRUST content_type (Flutter may send octet-stream)
        # ✅ Just ensure file exists
        if not file.filename:
            raise HTTPException(status_code=400, detail="No file uploaded")

        # Extract extension safely
        filename_parts = file.filename.split(".")
        file_ext = filename_parts[-1] if len(filename_parts) > 1 else "jpg"

        # Generate unique filename
        filename = f"{uuid.uuid4()}.{file_ext}"
        file_path = os.path.join(UPLOAD_DIR, filename)

        # Save file
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)

        # Public URL
        file_url = f"/uploads/profiles/{filename}"

        return {
            "success": True,
            "message": "Image uploaded successfully",
            "file_url": file_url
        }

    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ Upload error: {str(e)}")
        raise HTTPException(status_code=500, detail="File upload failed")
