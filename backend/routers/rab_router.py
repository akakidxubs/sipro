"""Fase 80 — endpoint RAB terstruktur (template tipe/add-on, ringkasan HPP & margin, draf SPK dari RAB)."""
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

import rab_engine as re_
from core_utils import serialize_doc
from db import ORG_ID
from rbac import assert_project_access, require_permission

router = APIRouter(prefix="/rab", tags=["rab"])


class TemplateIn(BaseModel):
    items: List[dict] = []


class AllocationIn(BaseModel):
    method: str


class DraftIn(BaseModel):
    project_id: str
    mode: str = "unit_addon"           # unit | addon | unit_addon | fasum | umum
    unit_ids: List[str] = []
    boq_item_ids: List[str] = []


def _org(user):
    return user.get("org_id", ORG_ID)


def _err(e):
    return HTTPException(status_code=400, detail=str(e))


@router.get("/options")
async def options(user: dict = Depends(require_permission("boq", "view"))):
    return {"data": {"facilities": [{"code": c, "label": l} for c, l in re_.FACILITIES],
                     "umum_kinds": [{"code": c, "label": l} for c, l in re_.UMUM_KINDS],
                     "allocations": re_.ALLOCATIONS}}


@router.get("/templates/{kind}")
async def list_templates(kind: str, user: dict = Depends(require_permission("boq", "view"))):
    if kind not in ("unit_type", "addon"):
        raise HTTPException(status_code=404, detail="Jenis template tidak dikenal.")
    return {"data": serialize_doc(await re_.list_templates(_org(user), kind))}


@router.get("/templates/{kind}/{ref_code}")
async def get_template(kind: str, ref_code: str, user: dict = Depends(require_permission("boq", "view"))):
    return {"data": serialize_doc(await re_.get_template(_org(user), kind, ref_code))}


@router.put("/templates/{kind}/{ref_code}")
async def save_template(kind: str, ref_code: str, p: TemplateIn,
                        user: dict = Depends(require_permission("boq", "update"))):
    try:
        return {"data": serialize_doc(await re_.save_template(_org(user), kind, ref_code, p.items, user.get("email")))}
    except ValueError as e:
        raise _err(e)


@router.get("/projects/{pid}/summary")
async def project_summary(pid: str, user: dict = Depends(require_permission("boq", "view"))):
    await assert_project_access(pid, user)
    return {"data": serialize_doc(await re_.project_summary(_org(user), pid))}


@router.put("/projects/{pid}/allocation")
async def set_allocation(pid: str, p: AllocationIn, user: dict = Depends(require_permission("boq", "update"))):
    await assert_project_access(pid, user)
    try:
        return {"data": {"allocation": await re_.set_allocation(_org(user), pid, p.method)}}
    except ValueError as e:
        raise _err(e)


@router.post("/spk-draft")
async def spk_draft(p: DraftIn, user: dict = Depends(require_permission("subcon", "view"))):
    await assert_project_access(p.project_id, user)
    try:
        if p.mode in ("fasum", "umum"):
            return {"data": serialize_doc(await re_.fasum_draft(_org(user), p.project_id, p.mode, p.boq_item_ids))}
        if not p.unit_ids:
            raise ValueError("Pilih minimal satu unit.")
        return {"data": serialize_doc(await re_.spk_draft(_org(user), p.project_id, p.unit_ids, p.mode))}
    except ValueError as e:
        raise _err(e)
