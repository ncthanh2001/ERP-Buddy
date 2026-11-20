from erp_buddy.ai.tools.base import BaseTool
from erp_buddy.ai.tools.documents import (
	CountDocuments,
	CreateDocument,
	GetDocument,
	ListDocuments,
	UpdateDocument,
)
from erp_buddy.ai.tools.knowledge import FindDocType, GetGuide, ListFeatures, SearchGuides
from erp_buddy.ai.tools.metadata import GetDocTypeInfo

TOOL_CLASSES: list[type[BaseTool]] = [
	SearchGuides,
	GetGuide,
	ListFeatures,
	FindDocType,
	GetDocTypeInfo,
	ListDocuments,
	CountDocuments,
	GetDocument,
	CreateDocument,
	UpdateDocument,
]


def get_tools() -> dict[str, BaseTool]:
	return {cls.name: cls() for cls in TOOL_CLASSES}
