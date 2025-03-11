import json
from fastapi import APIRouter, Depends, HTTPException, Query


from qualities.model.qualitiesModel import QualitiesCreate, QualitiesTable
from users.models.usermodel import UserTable
from users.routes.userAuth import get_current_user

router = APIRouter()

@router.post("/qualities/qualities-create")
async def createThings(body: QualitiesCreate):  # Use QualitiesCreate instead of QualitiesTable
    try:
        # Convert QualitiesCreate (Pydantic model) to QualitiesTable (MongoEngine document)
        savedata = QualitiesTable(**body.dict())
        savedata.save()  # Save to MongoDB
        return {
            "message": "Things data saved successfully"
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/qualities/get-all")
async def getAllqualities(
    user: UserTable = Depends(get_current_user),
    page: int = Query(1, ge=1),  # Default to page 1 and ensure it's >= 1
    per_page: int = Query(10, le=100),  # Default to 10 items per page, max 100
):
    skip_value = (page - 1) * per_page

    things = QualitiesTable.objects.skip(skip_value).limit(per_page).all()

    if not things:
        raise HTTPException(status_code=404, detail="No more items found")

    # Convert MongoEngine documents to dictionaries
    things_json = [thing.to_mongo().to_dict() for thing in things]

    return {
        "message": "All qualities data",
        "data": json.loads(things.to_json()),
        "page": page,
        "per_page": per_page,
    }

