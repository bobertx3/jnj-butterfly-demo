"""Next best action API: list and update actions from Lakebase."""

from datetime import date, datetime
from typing import Any, Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from server.db import db

router = APIRouter(prefix="/api/actions", tags=["actions"])

SCHEMA = "public"
TABLE = "next_best_action"


class ActionOut(BaseModel):
    id: int
    account_id: str
    contact_id: Optional[str]
    action_type: str
    title: str
    description: Optional[str]
    priority: str
    status: str
    due_date: Optional[date]
    created_at: datetime
    updated_at: datetime


class ActionUpdate(BaseModel):
    status: Optional[str] = None


@router.get("", response_model=list[ActionOut])
async def list_actions(
    status: Optional[str] = None,
    account_id: Optional[str] = None,
    limit: int = 50,
) -> list[ActionOut]:
    """List next best actions, optionally filtered by status or account_id."""
    pool = await db.get_pool()
    if not pool:
        return _mock_actions(limit)
    conditions = []
    params: list[Any] = []
    idx = 1
    if status:
        conditions.append(f"status = ${idx}")
        params.append(status)
        idx += 1
    if account_id:
        conditions.append(f"account_id = ${idx}")
        params.append(account_id)
        idx += 1
    params.append(limit)
    where = (" WHERE " + " AND ".join(conditions)) if conditions else ""
    q = f'SELECT id, account_id, contact_id, action_type, title, description, priority, status, due_date, created_at, updated_at FROM "{SCHEMA}"."{TABLE}"{where} ORDER BY due_date NULLS LAST, id LIMIT ${idx}'
    async with pool.acquire() as conn:
        rows = await conn.fetch(q, *params)
    return [_row_to_action(r) for r in rows]


@router.get("/{action_id}", response_model=ActionOut)
async def get_action(action_id: int) -> ActionOut:
    """Get a single next best action by id."""
    pool = await db.get_pool()
    if not pool:
        for a in _mock_actions(5):
            if a.id == action_id:
                return a
        raise HTTPException(status_code=404, detail="Action not found")
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            f'SELECT id, account_id, contact_id, action_type, title, description, priority, status, due_date, created_at, updated_at FROM "{SCHEMA}"."{TABLE}" WHERE id = $1',
            action_id,
        )
    if not row:
        raise HTTPException(status_code=404, detail="Action not found")
    return _row_to_action(row)


@router.patch("/{action_id}", response_model=ActionOut)
async def update_action(action_id: int, body: ActionUpdate) -> ActionOut:
    """Update an action (e.g. set status to completed or dismissed)."""
    pool = await db.get_pool()
    if not pool:
        raise HTTPException(status_code=503, detail="Database not configured")
    if body.status is None:
        return await get_action(action_id)
    async with pool.acquire() as conn:
        await conn.execute(
            f'UPDATE "{SCHEMA}"."{TABLE}" SET status = $1, updated_at = NOW() WHERE id = $2',
            body.status,
            action_id,
        )
        row = await conn.fetchrow(
            f'SELECT id, account_id, contact_id, action_type, title, description, priority, status, due_date, created_at, updated_at FROM "{SCHEMA}"."{TABLE}" WHERE id = $1',
            action_id,
        )
    if not row:
        raise HTTPException(status_code=404, detail="Action not found")
    return _row_to_action(row)


def _row_to_action(r: Any) -> ActionOut:
    return ActionOut(
        id=r["id"],
        account_id=r["account_id"],
        contact_id=r["contact_id"],
        action_type=r["action_type"],
        title=r["title"],
        description=r["description"],
        priority=r["priority"],
        status=r["status"],
        due_date=r["due_date"],
        created_at=r["created_at"],
        updated_at=r["updated_at"],
    )


def _mock_actions(limit: int) -> list[ActionOut]:
    """Fallback when Lakebase is not configured."""
    from datetime import timedelta
    base = datetime.utcnow()
    return [
        ActionOut(
            id=i,
            account_id=f"ACC-{i:06d}",
            contact_id=f"CON-{i:07d}" if i % 3 else None,
            action_type="product_demo",
            title="Schedule product demo",
            description="Offer a live demo of the requested product line.",
            priority="high" if i % 2 else "medium",
            status="pending",
            due_date=(base + timedelta(days=i)).date(),
            created_at=base,
            updated_at=base,
        )
        for i in range(1, min(limit + 1, 6))
    ]
