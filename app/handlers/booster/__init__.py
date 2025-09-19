from aiogram import Router
from .support import router as support_router
from .order_handling import router as order_handling_router
from .main_menu import router as main_menu_router
from .balance import router as balance_router
from .stats import router as stats_router

router = Router()
router.include_router(support_router)
router.include_router(order_handling_router)
router.include_router(main_menu_router)
router.include_router(balance_router)
router.include_router(stats_router)
