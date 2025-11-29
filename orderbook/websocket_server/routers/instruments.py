"""Instrument REST endpoints."""

from fastapi import APIRouter, HTTPException

from broadcast import broadcast_instruments_update
from state import instrument_service, market_maker_service

router = APIRouter(prefix="/api/instruments", tags=["Instruments"])


@router.get("")
async def list_instruments():
    instruments = instrument_service.list_instruments()
    return [inst.to_dict() for inst in instruments]


@router.post("")
async def add_instrument(data: dict):
    ticker = data.get("ticker")
    description = data.get("description", "")
    industry = data.get("industry", "")
    initial_price = data.get("initial_price")

    if not ticker:
        raise HTTPException(status_code=400, detail="Ticker is required")
    if initial_price is None:
        raise HTTPException(status_code=400, detail="initial_price is required")

    try:
        initial_price = float(initial_price)
    except (TypeError, ValueError):
        raise HTTPException(status_code=400, detail="initial_price must be numeric")

    if initial_price <= 0:
        raise HTTPException(status_code=400, detail="initial_price must be positive")

    instrument = instrument_service.add_instrument(
        ticker, description, industry, initial_price
    )
    if instrument:
        await market_maker_service.ensure_instrument(instrument)
        await broadcast_instruments_update()
        return instrument.to_dict()
    raise HTTPException(status_code=500, detail="Failed to add instrument")


@router.delete("/{symbol_id}")
async def remove_instrument(symbol_id: int):
    success = instrument_service.remove_instrument(symbol_id)
    if success:
        await market_maker_service.remove_instrument(symbol_id)
        await broadcast_instruments_update()
        return {"status": "success"}
    raise HTTPException(status_code=404, detail="Instrument not found")

