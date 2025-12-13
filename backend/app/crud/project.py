"""
Project CRUD Operations
Database operations for projects
"""

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from typing import Optional, List, Tuple
from uuid import UUID

from app.models.project import Project


async def get_project_by_id(
    db: AsyncSession,
    project_id: UUID,
    user_id: Optional[UUID] = None
) -> Optional[Project]:
    """Get a project by ID, optionally filtered by user"""
    query = select(Project).where(Project.id == project_id)
    if user_id:
        query = query.where(Project.user_id == user_id)
    result = await db.execute(query)
    return result.scalar_one_or_none()


async def get_projects_by_user(
    db: AsyncSession,
    user_id: UUID,
    skip: int = 0,
    limit: int = 20,
    status: Optional[str] = None,
) -> Tuple[List[Project], int]:
    """Get paginated projects for a user with total count"""
    # Base query
    base_query = select(Project).where(Project.user_id == user_id)

    if status:
        base_query = base_query.where(Project.status == status)

    # Get total count
    count_query = select(func.count()).select_from(base_query.subquery())
    total_result = await db.execute(count_query)
    total = total_result.scalar()

    # Get paginated results
    query = base_query.order_by(Project.created_at.desc()).offset(skip).limit(limit)
    result = await db.execute(query)
    projects = result.scalars().all()

    return list(projects), total


async def create_project(
    db: AsyncSession,
    user_id: UUID,
    customer_name: str,
    address: str,
    postal_code: str,
    pv_peak_power_kw: float,
    battery_capacity_kwh: float,
    annual_consumption_kwh: float,
    **kwargs
) -> Project:
    """Create a new project"""
    # Calculate battery power if not provided
    battery_power_kw = kwargs.get("battery_power_kw")
    if not battery_power_kw:
        battery_power_kw = battery_capacity_kwh * 0.5

    project = Project(
        user_id=user_id,
        customer_name=customer_name,
        address=address,
        postal_code=postal_code,
        pv_peak_power_kw=pv_peak_power_kw,
        battery_capacity_kwh=battery_capacity_kwh,
        battery_power_kw=battery_power_kw,
        annual_consumption_kwh=annual_consumption_kwh,
        status="draft",
        **{k: v for k, v in kwargs.items() if k != "battery_power_kw"}
    )
    db.add(project)
    await db.flush()
    await db.refresh(project)
    return project


async def update_project(
    db: AsyncSession,
    project: Project,
    **kwargs
) -> Project:
    """Update project fields"""
    for key, value in kwargs.items():
        if hasattr(project, key) and value is not None:
            setattr(project, key, value)
    await db.flush()
    await db.refresh(project)
    return project


async def delete_project(db: AsyncSession, project: Project) -> None:
    """Delete a project"""
    await db.delete(project)
    await db.flush()


async def get_project_with_simulations(
    db: AsyncSession,
    project_id: UUID,
    user_id: Optional[UUID] = None
) -> Optional[Project]:
    """Get project with eagerly loaded simulations"""
    query = select(Project).options(
        selectinload(Project.simulations)
    ).where(Project.id == project_id)

    if user_id:
        query = query.where(Project.user_id == user_id)

    result = await db.execute(query)
    return result.scalar_one_or_none()
