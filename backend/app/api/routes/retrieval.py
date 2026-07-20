from fastapi import APIRouter

from app.api.deps import CurrentUser, SessionDep
from app.models import RetrievalRequest, RetrievalResults
from app.services.retrieval import search_chunks

router = APIRouter(prefix="/retrieval", tags=["retrieval"])


@router.post("/search", response_model=RetrievalResults)
def search(
    request: RetrievalRequest,
    session: SessionDep,
    current_user: CurrentUser,
) -> RetrievalResults:
    results = search_chunks(
        session=session,
        owner_id=current_user.id,
        query=request.query,
        top_k=request.top_k,
    )
    return RetrievalResults(data=results)
