from fastapi import APIRouter
from fastapi import Depends
from fastapi import Request
from fastapi.responses import Response

from apps.webui.models.users import (
    UserResponse
)
from utils.misc import parse_duration
from utils.utils import (
    get_current_user,
    create_token,
)

router = APIRouter()


############################
# GetSessionUser
############################


@router.get("/", response_model=UserResponse)
async def get_session_user(
        request: Request, response: Response, user=Depends(get_current_user)
):
    token = create_token(
        data={"id": user.id},
        expires_delta=parse_duration(request.app.state.config.JWT_EXPIRES_IN),
    )

    # Set the cookie token
    response.set_cookie(
        key="token",
        value=token,
        httponly=True,  # Ensures the cookie is not accessible via JavaScript
    )

    return {
        "id": user.id,
        "email": user.email,
        "name": user.name,
        "role": user.role,
        "groups": user.groups,
        "profile_image_url": user.profile_image_url,
    }
