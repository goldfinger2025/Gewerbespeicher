"""
Component CRUD Operations
Database operations for components catalog
"""

from sqlalchemy import select, func, and_
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional, List, Tuple
from uuid import UUID

from app.models.component import Component


async def get_component_by_id(db: AsyncSession, component_id: UUID) -> Optional[Component]:
    """Get a component by ID"""
    result = await db.execute(select(Component).where(Component.id == component_id))
    return result.scalar_one_or_none()


async def get_components(
    db: AsyncSession,
    skip: int = 0,
    limit: int = 50,
    category: Optional[str] = None,
    manufacturer: Optional[str] = None,
    min_price: Optional[float] = None,
    max_price: Optional[float] = None,
    is_active: bool = True,
) -> Tuple[List[Component], int]:
    """Get paginated components with filters"""
    conditions = []

    if is_active:
        conditions.append(Component.is_active.is_(True))
    if category:
        conditions.append(Component.category == category)
    if manufacturer:
        conditions.append(Component.manufacturer == manufacturer)
    if min_price is not None:
        conditions.append(Component.unit_price_eur >= min_price)
    if max_price is not None:
        conditions.append(Component.unit_price_eur <= max_price)

    base_query = select(Component)
    if conditions:
        base_query = base_query.where(and_(*conditions))

    # Get total count
    count_query = select(func.count()).select_from(base_query.subquery())
    total_result = await db.execute(count_query)
    total = total_result.scalar()

    # Get paginated results
    query = base_query.order_by(Component.manufacturer, Component.model).offset(skip).limit(limit)
    result = await db.execute(query)
    components = result.scalars().all()

    return list(components), total


async def get_components_by_category(
    db: AsyncSession,
    category: str,
    is_active: bool = True
) -> List[Component]:
    """Get all components in a category"""
    conditions = [Component.category == category]
    if is_active:
        conditions.append(Component.is_active.is_(True))

    result = await db.execute(
        select(Component)
        .where(and_(*conditions))
        .order_by(Component.manufacturer, Component.model)
    )
    return list(result.scalars().all())


async def get_manufacturers(db: AsyncSession, category: Optional[str] = None) -> List[str]:
    """Get list of unique manufacturers"""
    query = select(Component.manufacturer).distinct()
    if category:
        query = query.where(Component.category == category)

    result = await db.execute(query.order_by(Component.manufacturer))
    return [row[0] for row in result.all()]


async def create_component(
    db: AsyncSession,
    category: str,
    manufacturer: str,
    model: str,
    **kwargs
) -> Component:
    """Create a new component"""
    component = Component(
        category=category,
        manufacturer=manufacturer,
        model=model,
        **kwargs
    )
    db.add(component)
    await db.flush()
    await db.refresh(component)
    return component


async def update_component(
    db: AsyncSession,
    component: Component,
    **kwargs
) -> Component:
    """Update component fields"""
    for key, value in kwargs.items():
        if hasattr(component, key) and value is not None:
            setattr(component, key, value)
    await db.flush()
    await db.refresh(component)
    return component


async def deactivate_component(db: AsyncSession, component: Component) -> Component:
    """Deactivate a component (soft delete)"""
    component.is_active = False
    await db.flush()
    await db.refresh(component)
    return component


async def delete_component(db: AsyncSession, component: Component) -> None:
    """Permanently delete a component"""
    await db.delete(component)
    await db.flush()
