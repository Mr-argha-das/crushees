import json
from fastapi import APIRouter, Depends, HTTPException, Query

from things.model.thingsModel import ThingsCreate, ThingsTable
from users.models.usermodel import UserTable
from users.routes.userAuth import get_current_user

router = APIRouter()

@router.post("/things/things-create")
async def createThings(body: ThingsCreate):
    try:
        savedata = ThingsTable(**body.dict())
        savedata.save()
        return {
            "message": "Things data saved successfully"
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/things/get-all")
async def getAllThings(
    user: UserTable = Depends(get_current_user),
    page: int = Query(1, ge=1),  # Default to page 1 and ensure it's >= 1
    per_page: int = Query(10, le=100),  # Default to 10 items per page, max 100
):
    skip_value = (page - 1) * per_page

    things = ThingsTable.objects.skip(skip_value).limit(per_page).all()

    if not things:
        raise HTTPException(status_code=404, detail="No more items found")

    things_json = [json.loads(thing.to_json()) for thing in things]

    return {
        "message": "All Things data",
        "data": things_json,
        "page": page,
        "per_page": per_page,
    }

@router.get("/things/search-all/")
async def getAllThings(query: str, user: UserTable = Depends(get_current_user)):
    things = ThingsTable.objects(title__icontains=query).all()
    if not things:
        raise HTTPException(status_code=404, detail="No items found matching the query")

    return {
        "message": "All Things data",
        "data": [json.loads(thing.to_json()) for thing in things]
    }
