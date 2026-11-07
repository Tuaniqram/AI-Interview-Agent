from typing import Optional
from uuid import UUID

from fastapi import APIRouter, BackgroundTasks, Depends, File, Form, Query, Request, UploadFile
from fastapi.responses import Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.middleware import authenticate
from app.auth.rbac import require_org_role, require_org_role_path, resolve_org_id
from app.candidates.auth import optional_candidate_auth, require_verified_candidate
from app.database.deps import get_db
from app.marketplace.schemas import (
    ApplicationInvitationResponse,
    ApplicationOutcomeRequest,
    ApplicationResponse,
    ApplyRequest,
    CandidateResponseRequest,
    CreatePublicInterviewRequest,
    FitScoreRequest,
    OrgListingResponse,
    OrgPublicInterviewResponse,
    PublicInterviewResponse,
    StartInterviewRequest,
    StartInterviewResponse,
    UpdatePublicInterviewRequest,
)
from app.services.audit_log import AuditLogService
from app.marketplace.fit_evaluation import run_application_fit_evaluation
from app.marketplace.notifications import (
    send_application_invitation_email,
    send_application_outcome_email,
    send_application_received_email,
)
from app.marketplace.service import (
    apply_to_public_interview,
    create_public_interview,
    delete_public_interview,
    get_application_invitation,
    get_application_resume,
    get_org_profile,
    get_public_interview,
    invite_application,
    list_candidate_applications,
    list_org_applications,
    list_org_public_interviews,
    list_organizations,
    queue_application_evaluation,
    respond_to_application,
    respond_to_invitation,
    set_application_fit,
    set_application_outcome,
    start_public_interview,
    update_public_interview,
)

router = APIRouter(prefix="/marketplace", tags=["marketplace"])


@router.get("/organizations", response_model=list[OrgListingResponse])
async def list_orgs(
    search: Optional[str] = Query(None),
    modes: Optional[str] = Query(None),
    expiry: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_db),
):
    return await list_organizations(search, modes, expiry, db)


@router.get("/organizations/{slug}")
async def org_profile(slug: str, db: AsyncSession = Depends(get_db)):
    return await get_org_profile(slug, db)


@router.get("/interviews/{interview_id}", response_model=PublicInterviewResponse)
async def get_interview(interview_id: UUID, db: AsyncSession = Depends(get_db)):
    return await get_public_interview(str(interview_id), db)


@router.post("/interviews/{interview_id}/start", response_model=StartInterviewResponse)
async def start_interview(
    interview_id: UUID,
    req: StartInterviewRequest,
    db: AsyncSession = Depends(get_db),
):
    return await start_public_interview(str(interview_id), req, db)


# ── Org CRUD for public interview listings ────────────────────────────


@router.post("/interviews", response_model=OrgPublicInterviewResponse)
async def create_listing(
    req: CreatePublicInterviewRequest,
    request: Request,
    org_id: str = Depends(resolve_org_id),
    _: None = Depends(require_org_role(["owner"])),
    db: AsyncSession = Depends(get_db),
):
    return await create_public_interview(
        org_id, req, db,
        actor_id=str(request.state.user.id) if hasattr(request.state, "user") else None,
        ip_address=request.client.host if request.client else None,
    )


@router.get("/org/{org_id}/interviews", response_model=list[OrgPublicInterviewResponse])
async def list_listings(
    org_id: str,
    _: None = Depends(require_org_role_path(["owner", "member", "viewer"])),
    db: AsyncSession = Depends(get_db),
):
    return await list_org_public_interviews(org_id, db)


@router.put("/interviews/{interview_id}", response_model=OrgPublicInterviewResponse)
async def update_listing(
    interview_id: UUID,
    req: UpdatePublicInterviewRequest,
    request: Request,
    _: None = Depends(require_org_role(["owner"])),
    db: AsyncSession = Depends(get_db),
):
    interview_id = str(interview_id)
    result = await update_public_interview(interview_id, req, db)
    audit = AuditLogService(db)
    await audit.log(
        action="marketplace.update",
        resource_type="public_interview",
        resource_id=interview_id,
        user_id=str(request.state.user.id) if hasattr(request.state, "user") else None,
        ip_address=request.client.host if request.client else None,
    )
    return result


@router.delete("/interviews/{interview_id}", status_code=204)
async def delete_listing(
    interview_id: UUID,
    request: Request,
    _: None = Depends(require_org_role(["owner"])),
    db: AsyncSession = Depends(get_db),
):
    interview_id = str(interview_id)
    await delete_public_interview(interview_id, db)
    audit = AuditLogService(db)
    await audit.log(
        action="marketplace.delete",
        resource_type="public_interview",
        resource_id=interview_id,
        user_id=str(request.state.user.id) if hasattr(request.state, "user") else None,
        ip_address=request.client.host if request.client else None,
    )


@router.post("/interviews/{interview_id}/apply", response_model=ApplicationResponse)
async def apply_to_interview(
    interview_id: UUID,
    background_tasks: BackgroundTasks,
    candidate_email: Optional[str] = Form(None),
    candidate_name: Optional[str] = Form(None),
    resume_document_id: Optional[UUID] = Form(None),
    resume: Optional[UploadFile] = File(None),
    candidate=Depends(optional_candidate_auth),
    db: AsyncSession = Depends(get_db),
):
    """Apply with a CV (multipart/form-data). Guests send email + name + CV.

    The fit evaluation runs after the response, so applying never waits on the LLM.
    """
    req = ApplyRequest(
        candidate_email=candidate_email,
        candidate_name=candidate_name,
        resume_document_id=resume_document_id,
    )
    application = await apply_to_public_interview(
        str(interview_id), req, db, candidate=candidate, resume=resume
    )
    if application.fit_status == "pending":
        background_tasks.add_task(send_application_received_email, str(application.id))
        background_tasks.add_task(run_application_fit_evaluation, str(application.id))
    return application


@router.get("/applications/me", response_model=list[ApplicationResponse])
async def my_applications(
    candidate=Depends(require_verified_candidate),
    db: AsyncSession = Depends(get_db),
):
    return await list_candidate_applications(candidate.id, db)


@router.get("/org/{org_id}/applications", response_model=list[ApplicationResponse])
async def org_applications(
    org_id: str,
    _: None = Depends(require_org_role_path(["owner", "member", "viewer"])),
    db: AsyncSession = Depends(get_db),
):
    return await list_org_applications(org_id, db)


@router.post("/applications/{application_id}/fit", response_model=ApplicationResponse)
async def set_fit(
    application_id: UUID,
    req: FitScoreRequest,
    org_id: str = Depends(resolve_org_id),
    _: None = Depends(require_org_role(["owner"])),
    db: AsyncSession = Depends(get_db),
):
    return await set_application_fit(str(application_id), req, org_id, db)


@router.post("/applications/{application_id}/evaluate", response_model=ApplicationResponse)
async def evaluate_application(
    application_id: UUID,
    background_tasks: BackgroundTasks,
    org_id: str = Depends(resolve_org_id),
    _: None = Depends(require_org_role(["owner"])),
    db: AsyncSession = Depends(get_db),
):
    """Re-run the automatic fit evaluation (e.g. after a failure)."""
    application = await queue_application_evaluation(str(application_id), org_id, db)
    background_tasks.add_task(run_application_fit_evaluation, str(application_id))
    return application


@router.get("/applications/{application_id}/resume")
async def download_application_resume(
    application_id: UUID,
    org_id: str = Depends(resolve_org_id),
    _: None = Depends(require_org_role(["owner", "member", "viewer"])),
    db: AsyncSession = Depends(get_db),
):
    """Download the CV of an application to the organization that received it."""
    content, filename = await get_application_resume(str(application_id), org_id, db)
    safe = filename.replace('"', "").replace("\r", "").replace("\n", "") or "cv.pdf"
    return Response(content, media_type="application/pdf", headers={"Content-Disposition": f'attachment; filename="{safe}"'})


@router.post("/applications/{application_id}/invite", response_model=ApplicationResponse)
async def invite_candidate(
    application_id: UUID,
    request: Request,
    background_tasks: BackgroundTasks,
    org_id: str = Depends(resolve_org_id),
    _: None = Depends(require_org_role(["owner"])),
    db: AsyncSession = Depends(get_db),
):
    actor_id = str(request.state.user.id) if hasattr(request.state, "user") else None
    application = await invite_application(str(application_id), org_id, actor_id, db)
    # The invite is already committed; an email failure must not undo it (it can be re-sent).
    background_tasks.add_task(send_application_invitation_email, str(application_id))
    return application


@router.post("/applications/{application_id}/outcome", response_model=ApplicationResponse)
async def record_outcome(
    application_id: UUID,
    req: ApplicationOutcomeRequest,
    request: Request,
    background_tasks: BackgroundTasks,
    org_id: str = Depends(resolve_org_id),
    _: None = Depends(require_org_role(["owner"])),
    db: AsyncSession = Depends(get_db),
):
    actor_id = str(request.state.user.id) if hasattr(request.state, "user") else None
    application = await set_application_outcome(str(application_id), req, org_id, actor_id, db)
    background_tasks.add_task(send_application_outcome_email, str(application_id))
    return application


@router.get("/application-invitations/{token}", response_model=ApplicationInvitationResponse)
async def view_application_invitation(token: str, db: AsyncSession = Depends(get_db)):
    """Public (no login): the emailed invite token is the credential."""
    return await get_application_invitation(token, db)


@router.post("/application-invitations/{token}/respond", response_model=ApplicationInvitationResponse)
async def respond_to_application_invitation(
    token: str,
    req: CandidateResponseRequest,
    db: AsyncSession = Depends(get_db),
):
    """Public (no login): accept or decline. Accepting returns the session id to start the interview."""
    return await respond_to_invitation(token, req.response, db)


@router.post("/applications/{application_id}/respond", response_model=ApplicationResponse)
async def candidate_respond(
    application_id: UUID,
    req: CandidateResponseRequest,
    candidate=Depends(require_verified_candidate),
    db: AsyncSession = Depends(get_db),
):
    return await respond_to_application(str(application_id), req, candidate.id, db)
