# -*- coding: utf-8 -*-
"""
🌐 AGI BRIDGE — Universal Deploy Connection System
📦 Version: 1.0.0 — Works with ANY System
👤 Creator: Thanwa Phupingbut | Rufio D'noto
🏷️ Brand: TPS Group & Genai
🔐 Entry Key: #AGI244 — Enter ONCE per installation

✅ คุณสมบัติหลัก:
   🔐 ใส่รหัส #AGI244 ครั้งเดียวตอนติดตั้ง — ไม่ต้องใส่ซ้ำ
   🔌 เชื่อมระบบใดๆ กับ Deploy-Auto ได้ทั้งหมด
   🚀 สั่ง Deploy ผ่านสะพานนี้ได้จากทุกที่
   📋 จัดการหลายระบบหลายรีโปได้ในที่เดียว
   🌐 พอร์ตเทเบิล — ติดตั้งที่ไหนก็ได้
   📖 API ครบถ้วน เชื่อมต่อกับแอป/เว็บอื่นได้
"""

import json
import uuid
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any
from pydantic import BaseModel, Field
from fastapi import FastAPI, HTTPException, Header, Depends, Body
from fastapi.middleware.cors import CORSMiddleware
import requests

from security import security, require_agi_access

# ==========================================
# 💾 DATA STORAGE
# ==========================================

class BridgeData:
    def __init__(self, root: str = "agi_bridge_data"):
        self.root = Path(root)
        self.root.mkdir(exist_ok=True)
        self.systems_file = self.root / "connected_systems.json"
        self.deploy_log_file = self.root / "deploy_history.json"
        self.da_config_file = self.root / "deploy_auto_config.json"
        self._init_files()

    def _init_files(self):
        for f in [self.systems_file, self.deploy_log_file, self.da_config_file]:
            if not f.exists():
                self._write(f, [] if "log" in f.name else {})

    def _read(self, path: Path):
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)

    def _write(self, path: Path, data):
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    # Systems
    def get_systems(self): return self._read(self.systems_file)
    def save_system(self, sys_id: str, data: dict):
        systems = self.get_systems()
        systems[sys_id] = data
        self._write(self.systems_file, systems)
    def delete_system(self, sys_id: str):
        systems = self.get_systems()
        if sys_id in systems: del systems[sys_id]
        self._write(self.systems_file, systems)

    # Deploy-Auto Config
    def get_da_config(self): return self._read(self.da_config_file)
    def save_da_config(self, url: str, api_key: str):
        self._write(self.da_config_file, {
            "url": url,
            "api_key_masked": api_key[:8] + "****" + api_key[-4:] if api_key else None,
            "connected_at": datetime.now().isoformat(),
            "status": "configured"
        })
        # เก็บค่าจริงในหน่วยความจำชั่วคราวสำหรับการทำงาน
        self._da_credentials = {"url": url, "api_key": api_key}

    def get_da_credentials(self):
        if hasattr(self, "_da_credentials"):
            return self._da_credentials
        return None

    # Deploy Log
    def add_log(self, entry: dict):
        logs = self._read(self.deploy_log_file)
        entry["time"] = datetime.now().isoformat()
        logs.insert(0, entry)
        self._write(self.deploy_log_file, logs)
    def get_logs(self, limit: int = 50):
        return self._read(self.deploy_log_file)[:limit]


db = BridgeData()

# ==========================================
# 🌉 BRIDGE SERVICE — เชื่อมทุกระบบกับ Deploy-Auto
# ==========================================

class BridgeService:
    def connect_deploy_auto(self, da_url: str, api_key: str) -> dict:
        """ตั้งค่าเชื่อมต่อกับ Deploy-Auto — ทำครั้งเดียว"""
        try:
            da_url = da_url.rstrip("/")
            db.save_da_config(da_url, api_key)
            return {
                "ok": True,
                "message": "✅ ตั้งค่า Deploy-Auto สำเร็จ — พร้อมใช้งานตลอด",
                "url": da_url
            }
        except Exception as e:
            return {"ok": False, "error": str(e)}

    def register_system(self, name: str, repo_url: str, desc: str = "") -> dict:
        """ลงทะเบียนระบบที่ต้องการให้ Deploy-Auto จัดการ"""
        sys_id = f"sys_{uuid.uuid4().hex[:10]}"
        system_data = {
            "id": sys_id,
            "name": name,
            "repo_url": repo_url,
            "description": desc,
            "created_at": datetime.now().isoformat(),
            "last_deploy": None,
            "status": "registered"
        }
        db.save_system(sys_id, system_data)
        db.add_log({"action": "register_system", "system": name, "id": sys_id})
        return {"ok": True, "system": system_data}

    def trigger_deploy(self, system_id: str, branch: str = "main") -> dict:
        """สั่ง Deploy ระบบที่ลงทะเบียนผ่าน Deploy-Auto"""
        da = db.get_da_credentials()
        if not da:
            return {"ok": False, "message": "⚠️ ยังไม่ได้ตั้งค่า Deploy-Auto — ไปที่ /setup/deploy-auto ก่อน"}
        
        systems = db.get_systems()
        if system_id not in systems:
            return {"ok": False, "message": "❌ ไม่พบระบบที่ระบุ"}
        
        system = systems[system_id]
        repo_name = system["repo_url"].split("/")[-1].replace(".git", "")
        
        try:
            # ส่งคำสั่งไปยัง Deploy-Auto
            headers = {
                "Content-Type": "application/json",
                "X-API-Key": da["api_key"]
            }
            payload = {
                "repository": repo_name,
                "branch": branch,
                "source": "AGI-Bridge",
                "system_name": system["name"]
            }
            
            # ทดสอบ endpoint — ปรับตาม Deploy-Auto จริง
            r = requests.post(
                f"{da['url']}/api/deploy/trigger",
                json=payload,
                headers=headers,
                timeout=30
            )
            
            if r.status_code in [200, 201, 202]:
                system["last_deploy"] = datetime.now().isoformat()
                system["status"] = "deploying"
                db.save_system(system_id, system)
                db.add_log({
                    "action": "deploy_started",
                    "system": system["name"],
                    "repo": repo_name,
                    "branch": branch,
                    "status": "success"
                })
                return {
                    "ok": True,
                    "message": f"🚀 ส่งคำสั่ง Deploy ไปยัง {system['name']} สำเร็จ",
                    "system": system["name"],
                    "repo": repo_name,
                    "branch": branch,
                    "deploy_time": datetime.now().isoformat()
                }
            else:
                db.add_log({
                    "action": "deploy_failed",
                    "system": system["name"],
                    "status": "error",
                    "code": r.status_code
                })
                return {"ok": False, "message": f"⚠️ Deploy-Auto ตอบกลับ: {r.status_code}"}
        
        except requests.exceptions.ConnectionError:
            db.add_log({
                "action": "deploy_error",
                "system": system["name"],
                "error": "connection_failed"
            })
            return {
                "ok": False,
                "message": "❌ ไม่สามารถติดต่อ Deploy-Auto — ตรวจสอบ URL และการเชื่อมต่อ"
            }
        except Exception as e:
            db.add_log({
                "action": "deploy_error",
                "system": system["name"],
                "error": str(e)
            })
            return {"ok": False, "message": f"❌ เกิดข้อผิดพลาด: {str(e)}"}

    def get_status(self) -> dict:
        """สถานะรวมของระบบสะพาน"""
        da_config = db.get_da_config()
        systems = db.get_systems()
        logs = db.get_logs(10)
        return {
            "deploy_auto_configured": da_config.get("status") == "configured",
            "connected_systems": len(systems),
            "systems": list(systems.values()),
            "recent_activity": logs
        }


bridge = BridgeService()

# ==========================================
# 📋 DATA MODELS
# ==========================================

class SetupDeployAuto(BaseModel):
    deploy_auto_url: str = Field(..., description="URL ของระบบ Deploy-Auto")
    api_key: str = Field(..., description="API Key จาก Deploy-Auto")

class RegisterSystem(BaseModel):
    name: str = Field(..., max_length=100, description="ชื่อระบบที่ต้องการจัดการ")
    repo_url: str = Field(..., description="ลิงก์ GitHub รีโป")
    description: str = ""

class DeployRequest(BaseModel):
    system_id: str
    branch: str = "main"

# ==========================================
# 🚀 FASTAPI APP
# ==========================================

app = FastAPI(
    title="🌐 AGI Bridge — Universal Deploy Connector",
    description="สะพานกลางเชื่อมทุกระบบกับ Deploy-Auto — ติดตั้งที่ไหนก็ได้",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ==========================================
# 🏠 PUBLIC ENDPOINTS
# ==========================================

@app.get("/")
def root():
    return {
        "system": "🌐 AGI BRIDGE — Universal Deploy Connector",
        "version": "1.0.0",
        "status": "✅ INSTALLED",
        "note": "⚠️ ใส่รหัส #AGI244 ผ่าน Header: AGI-Access: #AGI244",
        "first_time": "ไปที่ /setup/deploy-auto เพื่อเชื่อมต่อ Deploy-Auto ครั้งแรก",
        "endpoints": {
            "ตรวจสอบสิทธิ์": "/auth/verify",
            "ตั้งค่า Deploy-Auto": "/setup/deploy-auto",
            "ลงทะเบียนระบบ": "/systems/register",
            "รายการระบบ": "/systems",
            "สั่ง Deploy": "/deploy/trigger",
            "สถานะ": "/status",
            "ประวัติ": "/logs",
            "เอกสาร": "/docs"
        },
        "creator": "Thanwa Phupingbut | Rufio D'noto",
        "brand": "TPS Group & Genai"
    }

@app.get("/auth/verify")
def verify_access(result: Any = Depends(require_agi_access)):
    """🔑 ตรวจสอบรหัสเข้าใช้ — ใส่ #AGI244 ครั้งแรก"""
    if isinstance(result, dict) and "new_session" in result:
        return {
            "ok": True,
            "message": result["message"],
            "session_token": result["new_session"],
            "note": "✅ บันทึกสิทธิ์สำเร็จ — ใช้ Session-Token นี้ส่งใน Header AGI-Access แทนรหัสในครั้งต่อไป"
        }
    return {"ok": True, "message": "✅ สิทธิ์ถูกต้อง — พร้อมใช้งาน"}

# ==========================================
# ⚙️ SETUP — ต้องมีสิทธิ์
# ==========================================

@app.post("/setup/deploy-auto")
def setup_deploy_auto(config: SetupDeployAuto, _ = Depends(require_agi_access)):
    """🔌 เชื่อมต่อกับ Deploy-Auto — ทำครั้งเดียว"""
    return bridge.connect_deploy_auto(config.deploy_auto_url, config.api_key)

# ==========================================
# 🖥️ SYSTEMS — จัดการระบบที่เชื่อมต่อ
# ==========================================

@app.post("/systems/register")
def register_system(sys: RegisterSystem, _ = Depends(require_agi_access)):
    """➕ ลงทะเบียนระบบที่ต้องการให้ Deploy-Auto จัดการ"""
    return bridge.register_system(sys.name, sys.repo_url, sys.description)

@app.get("/systems")
def list_systems(_ = Depends(require_agi_access)):
    """📋 ดูรายการระบบทั้งหมดที่ลงทะเบียน"""
    return {"systems": list(db.get_systems().values())}

@app.delete("/systems/{system_id}")
def remove_system(system_id: str, _ = Depends(require_agi_access)):
    """🗑️ ลบระบบออกจากรายการ"""
    systems = db.get_systems()
    if system_id not in systems:
        raise HTTPException(404, "ไม่พบระบบ")
    name = systems[system_id]["name"]
    db.delete_system(system_id)
    db.add_log({"action": "remove_system", "system": name})
    return {"ok": True, "message": f"ลบระบบ {name} แล้ว"}

# ==========================================
# 🚀 DEPLOY — สั่งทำงาน
# ==========================================

@app.post("/deploy/trigger")
def trigger_deploy(req: DeployRequest, _ = Depends(require_agi_access)):
    """🚀 สั่ง Deploy ระบบที่เลือกผ่าน Deploy-Auto"""
    return bridge.trigger_deploy(req.system_id, req.branch)

@app.get("/status")
def system_status(_ = Depends(require_agi_access)):
    """📊 สถานะรวมของสะพานและระบบทั้งหมด"""
    return bridge.get_status()

@app.get("/logs")
def deploy_logs(limit: int = 50, _ = Depends(require_agi_access)):
    """📋 ประวัติการทำงานทั้

