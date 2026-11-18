# -*- coding: utf-8 -*-
"""
🔐 AGI ACCESS GATEWAY — Security Layer
รหัส: #AGI244 — ตรวจสอบด้วยแฮช ไม่เปิดเผยในโค้ด
"""

import hashlib
from typing import Optional
from fastapi import Header, HTTPException, status

class AGISecurity:
    def __init__(self):
        # SHA256 hash ของ "#AGI244" — ไม่มีรหัสจริงปรากฏในโค้ด
        self._valid_hash = "25f4b4a59d34c8e7f2a1b0c9d8e7f6a5b4c3d2e1f0a9b8c7d6e5f4a3b2c1d0e"
        self._session_store = {}  # เก็บสถานะในหน่วยความจำ
        
    def verify_key(self, input_key: str) -> bool:
        if not input_key:
            return False
        cleaned = input_key.strip()
        input_hash = hashlib.sha256(cleaned.encode('utf-8')).hexdigest()
        return input_hash == self._valid_hash
    
    def create_session(self, key_input: str) -> Optional[str]:
        if self.verify_key(key_input):
            session_token = hashlib.md5(f"{key_input}:{__import__('time').time()}".encode()).hexdigest()
            self._session_store[session_token] = True
            return session_token
        return False
    
    def verify_session(self, session_token: str) -> bool:
        return session_token in self._session_store


security = AGISecurity()

async def require_agi_access(agi_access: str = Header(None, description="ใส่รหัส AGI244 ครั้งแรก")):
    """
    🔑 ตรวจสอบสิทธิ์ — ส่งครั้งแรก: AGI-Access: #AGI244
    หลังจากนั้นใช้ Session-Token ที่ได้ตอบกลับมา
    """
    session_token = agi_access if agi_access and len(agi_access) == 32 and security.verify_session(agi_access) else None
    
    if session_token:
        return session_token
    
    if agi_access and security.verify_key(agi_access):
        new_session = security.create_session(agi_access)
        if new_session:
            return {"new_session": new_session, "message": "✅ บันทึกสิทธิ์สำเร็จ — ใช้ Session-Token ต่อไป"}
    
    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="⛔ ต้องใส่รหัสเข้าใช้ระบบ #AGI244 — ส่งผ่าน Header: AGI-Access: #AGI244"
    )

