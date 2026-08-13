"""Import every model so that Base.metadata is fully populated."""
from app.db.session import Base  # noqa: F401
from app.models.user import User  # noqa: F401
from app.models.category import Category  # noqa: F401
from app.models.supplier import Supplier  # noqa: F401
from app.models.product import Product  # noqa: F401
from app.models.stock_movement import StockMovement  # noqa: F401
