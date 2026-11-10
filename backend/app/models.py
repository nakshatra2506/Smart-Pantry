from sqlalchemy import String, Integer, Float, Date, DateTime, ForeignKey, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from datetime import datetime, date
from .db import Base

class Item(Base):
    __tablename__ = 'items'
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(120), unique=True, index=True)
    category: Mapped[str] = mapped_column(String(60), default='Other')
    unit: Mapped[str] = mapped_column(String(20), default='unit')
    quantity: Mapped[float] = mapped_column(Float, default=0)
    min_stock: Mapped[float] = mapped_column(Float, default=5)
    unit_cost: Mapped[float] = mapped_column(Float, default=0)
    supplier: Mapped[str] = mapped_column(String(120), default='')
    batches: Mapped[list['Batch']] = relationship(back_populates='item', cascade='all, delete-orphan')

class Batch(Base):
    __tablename__ = 'batches'
    id: Mapped[int] = mapped_column(primary_key=True)
    item_id: Mapped[int] = mapped_column(ForeignKey('items.id', ondelete='CASCADE'))
    quantity: Mapped[float] = mapped_column(Float, default=0)
    expiry_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    received_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    item: Mapped[Item] = relationship(back_populates='batches')

class Sale(Base):
    __tablename__ = 'sales'
    id: Mapped[int] = mapped_column(primary_key=True)
    item_id: Mapped[int] = mapped_column(ForeignKey('items.id'))
    quantity: Mapped[float] = mapped_column(Float)
    unit_price: Mapped[float] = mapped_column(Float, default=0)
    sold_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, index=True)
    note: Mapped[str] = mapped_column(String(250), default='')
    item: Mapped[Item] = relationship()

class Waste(Base):
    __tablename__ = 'waste'
    id: Mapped[int] = mapped_column(primary_key=True)
    item_id: Mapped[int] = mapped_column(ForeignKey('items.id'))
    quantity: Mapped[float] = mapped_column(Float)
    reason: Mapped[str] = mapped_column(String(100), default='Expired')
    wasted_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    item: Mapped[Item] = relationship()

class Movement(Base):
    __tablename__ = 'movements'
    id: Mapped[int] = mapped_column(primary_key=True)
    item_id: Mapped[int] = mapped_column(ForeignKey('items.id'))
    movement_type: Mapped[str] = mapped_column(String(20))
    quantity: Mapped[float] = mapped_column(Float)
    note: Mapped[str] = mapped_column(Text, default='')
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    item: Mapped[Item] = relationship()
