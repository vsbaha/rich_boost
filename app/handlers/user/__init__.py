from aiogram import Router
from .profile import router as profile_router
from .balance import router as balance_router    

router = Router()
router.include_router(profile_router)
router.include_router(balance_router)
# router.include_router(другие_роутеры)