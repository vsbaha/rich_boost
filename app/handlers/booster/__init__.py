from aiogram import Router
from .support import router as support_router

router = Router()
router.include_router(support_router) 
