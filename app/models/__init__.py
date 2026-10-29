"""app/models/__init__.py"""
from .user import User
from .application import Application, ApplicationHistory
from .business_details import BusinessDetails
from .partner import Partner
from .premises import Premises
from .building_owner import BuildingOwner
from .pharmacist import Pharmacist
from .declaration import Declaration
from .payment import Payment
from .attachment import Attachment
from .generated_document import GeneratedDocument

__all__ = [
    'User', 'Application', 'ApplicationHistory',
    'BusinessDetails', 'Partner', 'Premises',
    'BuildingOwner', 'Pharmacist', 'Declaration',
    'Payment', 'Attachment', 'GeneratedDocument',
]
