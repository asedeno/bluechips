"""
Handle expenditures
"""

import logging

from decimal import Decimal, InvalidOperation

from bluechips.lib.base import *

from pylons import request, app_globals as g
from pylons.decorators.rest import dispatch_on
from pylons.decorators import validate
from pylons.controllers.util import abort

from formencode import validators, Schema
from formencode.foreach import ForEach
from formencode.variabledecode import NestedVariables

from mailer import Message

log = logging.getLogger(__name__)


class ShareSchema(Schema):
    "Validate individual user shares."
    allow_extra_fields = False
    user_id = validators.Int(not_empty=True)
    amount = validators.Number(not_empty=True)


class ExpenditureSchema(Schema):
    "Validate an expenditure."
    allow_extra_fields = False
    pre_validators = [NestedVariables()]
    spender_id = validators.Int(not_empty=True)
    amount = model.types.CurrencyValidator(not_empty=True)
    description = validators.UnicodeString()
    date = validators.DateConverter()
    shares = ForEach(ShareSchema)
    

class SpendController(BaseController):
    def index(self):
        return self.edit()
    
    def edit(self, id=None):
        c.users = meta.Session.query(model.User.id, model.User)
        if id is None:
            c.title = 'Add a New Expenditure'
            c.expenditure = model.Expenditure()
            c.expenditure.spender_id = request.environ['user'].id

            num_residents = meta.Session.query(model.User).\
                    filter_by(resident=True).count()
            # Pre-populate split percentages for an even split.
            c.values = {}
            for ii, user_row in enumerate(c.users):
                user_id, user = user_row
                if user.resident:
                    val = Decimal(100) / Decimal(num_residents)
                else:
                    val = 0
                c.values['shares-%d.amount' % ii] = val
        else:
            c.title = 'Edit an Expenditure'
            c.expenditure = meta.Session.query(model.Expenditure).get(id)
            if c.expenditure is None:
                abort(404)
            c.values = {}
            for ii, user_row in enumerate(c.users):
                user_id, user = user_row
                try:
                    share = [s.share for s in c.expenditure.splits
                             if s.user == user][0]
                    if c.expenditure.amount == 0:
                        percent = 0
                    else:
                        percent = (Decimal(100) * Decimal(int(share)) /
                                   Decimal(int(c.expenditure.amount))).\
                                quantize(Decimal("0.001"))
                except IndexError:
                    percent = 0
                c.values['shares-%d.amount' % ii] = percent

        return render('/spend/index.mako')

    @validate(schema=ExpenditureSchema(), form='edit', variable_decode=True)
    def update(self, id=None):
        # Either create a new object, or, if we're editing, get the
        # old one
        if id is None:
            e = model.Expenditure()
            meta.Session.add(e)
            op = 'created'
        else:
            e = meta.Session.query(model.Expenditure).get(id)
            if e is None:
                abort(404)
            op = 'updated'
        
        # Set the fields that were submitted
        shares = self.form_result.pop('shares')
        update_sar(e, self.form_result)

        users = dict(meta.Session.query(model.User.id, model.User).all())
        split_dict = {}
        for share_params in shares:
            user = users[share_params['user_id']]
            split_dict[user] = Decimal(str(share_params['amount']))
        e.split(split_dict)
        
        meta.Session.commit()
       
        show = ("Expenditure of %s paid for by %s %s." %
                (e.amount, e.spender, op))
        h.flash(show)

        # Send email notification to involved users if they have an email set.
        involved_users = set(sp.user for sp in e.splits if sp.share != 0)
        involved_users.add(e.spender)
        body = render('/emails/expenditure.txt',
                      extra_vars={'expenditure': e,
                                  'op': op})
        g.handle_notification(involved_users, show, body)

        return h.redirect_to('/')
