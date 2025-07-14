from aiogram import Router
from .profile import router as profile_router
from .balance import router as balance_router    
from .support import router as support_router
from .bonus import router as bonus_router

router = Router()
router.include_router(profile_router)
router.include_router(balance_router)
router.include_router(support_router)
router.include_router(bonus_router)