from mongoengine import Document, ListField, ReferenceField
from ganabosques_orm.collections.enterprise import Enterprise
from ganabosques_orm.collections.analysis import Analysis
from ganabosques_orm.collections.farmrisk import FarmRisk

class EnterpriseRisk(Document):
    """Auto-generated MongoDB collection: EnterpriseRisk"""
    meta = {'collection': 'enterpriserisk'}
    
    enterprise_id = ReferenceField(Enterprise)
    analysis_id = ReferenceField(Analysis)
    risk_input = ListField(ReferenceField(FarmRisk))  
    risk_output = ListField(ReferenceField(FarmRisk)) 
