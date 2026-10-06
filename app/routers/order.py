import logging
from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app import models, schemas
from app.dependencies import get_db, get_current_member
from app.ai.rag.semantic_cache import semantic_cache
from app.services import order_service

router = APIRouter(prefix="/orders", tags=["orders"])
logger = logging.getLogger("api.order")


@router.post("", response_model=schemas.OrderResponse, status_code=status.HTTP_201_CREATED)
def create_order(
    body: schemas.OrderCreate,
    db: Session = Depends(get_db),
    current_member: models.Member = Depends(get_current_member),
):
    try:
        order, _ = order_service.place_order(db, current_member.id, body.product_id, body.quantity)
    except Exception as e:
        logger.warning("주문 실패 member_id=%s product_id=%s quantity=%s 사유=%s",
                       current_member.id, body.product_id, body.quantity, e)
        raise
    logger.info("주문 생성 order_id=%s member_id=%s product_id=%s quantity=%s",
                order.id, current_member.id, body.product_id, body.quantity)

    # 주문 발생 시 해당 사용자의 캐시만 삭제
    semantic_cache.flush_by_member(current_member.id)

    return order


@router.get("/me", response_model=List[schemas.OrderResponse])
def my_orders(
    db: Session = Depends(get_db),
    current_member: models.Member = Depends(get_current_member),
):
    return order_service.list_my_orders(db, current_member.id)


@router.delete("/{order_id}", status_code=status.HTTP_204_NO_CONTENT)
def cancel_order(
    order_id: int,
    db: Session = Depends(get_db),
    current_member: models.Member = Depends(get_current_member),
):
    try:
        order_service.cancel_order(db, current_member.id, order_id)
    except ValueError as e:
        logger.warning("주문 취소 실패 order_id=%s member_id=%s 사유=%s", order_id, current_member.id, e)
        raise HTTPException(status_code=400, detail=str(e))
    logger.info("주문 취소 order_id=%s member_id=%s", order_id, current_member.id)

