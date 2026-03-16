"""Shipping models."""

from datetime import datetime
import enum

from sqlalchemy import Column, DateTime, Enum, Float, Integer, String
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()


class ShippingStatus(str, enum.Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    SHIPPED = "shipped"
    DELIVERED = "delivered"
    FAILED = "failed"


class Shipment(Base):
    __tablename__ = "shipments"

    id = Column(Integer, primary_key=True, index=True)
    order_id = Column(String(255), unique=True, index=True, nullable=False)
    address = Column(String(1000), nullable=False)
    method_code = Column(String(50), nullable=False)
    method_name = Column(String(100), nullable=False)
    fee = Column(Float, nullable=False)
    estimated_days = Column(Integer, nullable=False)
    status = Column(Enum(ShippingStatus), default=ShippingStatus.PENDING, nullable=False)

    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
