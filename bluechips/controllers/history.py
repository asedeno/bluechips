"""
Display old transactions
"""

import logging
from pylons import request

from bluechips.lib.base import *
from bluechips.lib.totals import *

import sqlalchemy as sa
from sqlalchemy import orm

log = logging.getLogger(__name__)

class HistoryController(BaseController):
    def index(self):
        c.title = 'History'
        
        c.tags = meta.Session.query(model.Tag).order_by([sa.func.lower(model.Tag.name)])
        c.expenditures = meta.Session.query(model.Expenditure).\
                options(orm.eagerload('splits')).all()
        c.transfers = meta.Session.query(model.Transfer).all()

        return render('/history/index.mako')


    def tag(self, id=None):
        c.title = 'History'

        c.tags = meta.Session.query(model.Tag).order_by([sa.func.lower(model.Tag.name)])
        c.tag = meta.Session.query(model.Tag).filter_by(id=id).all()[0]
        c.expenditures = c.tag.expenditures
        c.total = sum([e.amount for e in c.expenditures])
        c.share = sum([e.share(request.environ['user']) for e in c.expenditures])

        return render('/history/tag.mako')
