"""Model package that re-exports domain modules for backward compatibility."""

from .rbac import Permission, Role, User, role_permissions
from .location import Location, Profile, SalesProfile, Supplier
from .product import FAQEntry, IMEIHistory, Product, ProductIMEI, Stock, StockHistory
from .order import (
    Order,
    OrderItem,
    Return,
    ReturnItem,
    StockTransfer,
    TradeIn,
    TradeInPolicy,
)
from .ai import AIProfileConfig, Customer, InteractionLog, TrainingQueue
from .finance import Bank, FinancingOption
from .photos import PhotoRequest, PhotoRequestMediaItem
from .ai import ProcessedMessage
from .system import SystemConfig
from .control import (
    AuditLog,
    LocationDailyClose,
    PhysicalInventoryCount,
    PhysicalInventoryCountItem,
    PurchaseReceipt,
    PurchaseReceiptItem,
    UserLocationAccess,
)

__all__ = [
    "Permission",
    "Role",
    "User",
    "role_permissions",
    "Location",
    "Profile",
    "SalesProfile",
    "Supplier",
    "Product",
    "ProductIMEI",
    "Stock",
    "StockHistory",
    "FAQEntry",
    "IMEIHistory",
    "Order",
    "OrderItem",
    "StockTransfer",
    "TradeIn",
    "Return",
    "ReturnItem",
    "TradeInPolicy",
    "AIProfileConfig",
    "Customer",
    "InteractionLog",
    "TrainingQueue",
    "ProcessedMessage",
    "Bank",
    "FinancingOption",
    "PhotoRequest",
    "PhotoRequestMediaItem",
    "SystemConfig",
    "UserLocationAccess",
    "AuditLog",
    "PurchaseReceipt",
    "PurchaseReceiptItem",
    "PhysicalInventoryCount",
    "PhysicalInventoryCountItem",
    "LocationDailyClose",
]


