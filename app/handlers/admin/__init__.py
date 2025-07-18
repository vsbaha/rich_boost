from aiogram import Router
from .button_user import router as users_router
from .payments import router as payments_router
from .admin_promo import router as promo_router

router = Router()
router.include_router(users_router)
router.include_router(payments_router)
router.include_router(promo_router)