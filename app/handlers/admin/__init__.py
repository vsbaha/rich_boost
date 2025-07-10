from aiogram import Router
from .button_user import router as users_router
# from .settings import router as settings_router  # если появятся другие разделы

router = Router()
router.include_router(users_router)
# router.include_router(settings_router)