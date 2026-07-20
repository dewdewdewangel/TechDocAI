from fastapi import APIRouter, Depends
from sqlmodel import col, func, select

from app.api.deps import SessionDep, get_current_active_superuser
from app.models import AuditLog, AuditLogPublic, AuditLogsPublic

router = APIRouter(
    prefix="/audit-logs",
    tags=["audit-logs"],
    dependencies=[Depends(get_current_active_superuser)],
)


@router.get("/", response_model=AuditLogsPublic)
def read_audit_logs(
    session: SessionDep,
    skip: int = 0,
    limit: int = 100,
) -> AuditLogsPublic:
    count = session.exec(select(func.count()).select_from(AuditLog)).one()
    logs = session.exec(
        select(AuditLog)
        .order_by(col(AuditLog.created_at).desc())
        .offset(skip)
        .limit(min(limit, 500))
    ).all()
    return AuditLogsPublic(
        data=[AuditLogPublic.model_validate(log) for log in logs],
        count=count,
    )
