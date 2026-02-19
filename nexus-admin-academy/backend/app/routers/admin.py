from fastapi import APIRouter

from . import admin_content, admin_quiz, admin_students, admin_tickets

router = APIRouter()
router.include_router(admin_quiz.router)
router.include_router(admin_tickets.router)
router.include_router(admin_students.router)
router.include_router(admin_content.router)
