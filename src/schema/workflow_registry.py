from sqlalchemy import Column, Integer, String, UniqueConstraint
from sqlalchemy.dialects.mysql import LONGTEXT
from .init_db import Base
from pydantic import BaseModel


class WorkflowRegistryModel(BaseModel):
    name: str
    version: str

    class Config:
        orm_mode = True


class WorkflowRegistry(Base):
    __tablename__ = "workflow_registry"
    __table_args__ = (
        UniqueConstraint('name', 'version', name='uq_name_version'),
    )

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)  # PK of table
    name = Column(String(255), nullable=False)
    version = Column(String(255), nullable=False)
    spec_file_content = Column(LONGTEXT, nullable=False)
    input_file_content = Column(LONGTEXT, nullable=True)
    username = Column(String(255), nullable=False)
    group = Column(String(255), nullable=False)
