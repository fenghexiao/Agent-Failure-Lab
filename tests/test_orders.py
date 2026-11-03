import pytest
from pydantic import ValidationError

from app.models import GetOrderArgs
from tools.orders import get_order


