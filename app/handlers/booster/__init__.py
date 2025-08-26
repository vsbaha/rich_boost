from aiogram import Router
from .support import router as support_router
from .order_handling import router as order_handling_router
from .menu import router as menu_router

router = Router()
router.include_router(support_router)
router.include_router(order_handling_router)
router.include_router(menu_router) 
