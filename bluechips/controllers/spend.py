"""
Handle expenditures
"""

from __future__ import division
import logging

import re
from decimal import Decimal, InvalidOperation

from bluechips.lib.base import *

from pylons import request, app_globals as g
from pylons.decorators import validate
from pylons.decorators.secure import authenticate_form
from pylons.controllers.util import abort

import formencode
from formencode import validators, Schema
from formencode.foreach import ForEach
from formencode.variabledecode import NestedVariables
from formencode.schema import SimpleFormValidator

from mailer import Message

log = logging.getLogger(__name__)

class ExpenditureExpression(validators.FancyValidator):
    goodChars = set('1234567890.+-/*() ')

    def _to_python(self, value, state):
        if (not set(value) <= self.goodChars or
            re.search(r'([\+\-\*\/])\1', value)):
            raise formencode.Invalid("Expression contains illegal characters", value, state)

        if value == '':
            return value, Decimal("0")

        try:
            number = eval(value)
            return value, Decimal(str(number))
        except:
            raise formencode.Invalid("Not a valid mathematical expression", value, state)


class ShareSchema(Schema):
    "Validate individual user shares."
    allow_extra_fields = False
    user_id = validators.Int(not_empty=True)
    amount = ExpenditureExpression()


def validate_state(value_dict, state, validator):
    if all(s['amount'] == 0 for s in value_dict['shares']):
        return {'shares-0.amount': 'Need at least one non-zero share'}
ValidateNotAllZero = SimpleFormValidator(validate_state)


class ExpenditureSchema(Schema):
    "Validate an expenditure."
    allow_extra_fields = False
    pre_validators = [NestedVariables()]
    spender_id = validators.Int(not_empty=True)
    amount = model.types.CurrencyValidator(not_empty=True)
    description = validators.UnicodeString(not_empty=True)
    date = validators.DateConverter()
    shares = ForEach(ShareSchema)
    chained_validators = [ValidateNotAllZero]
    

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
                val = 0
                if user.resident:
                    val = Decimal(100) / Decimal(num_residents)
                c.values['shares-%d.amount' % ii] = val
        else:
            c.title = 'Edit an Expenditure'
            c.expenditure = meta.Session.query(model.Expenditure).get(id)
            if c.expenditure is None:
                abort(404)
            c.values = {}
            for ii, user_row in enumerate(c.users):
                user_id, user = user_row
                shares_by_user = dict(((sp.user, sp.share_text) for sp
                                       in c.expenditure.splits))
                share = shares_by_user.get(user, '')
                c.values['shares-%d.amount' % ii] = share

        return render('/spend/index.mako')

    @redirect_on_get('edit')
    @authenticate_form
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
        split_text_dict = {}
        for share_params in shares:
            user = users[share_params['user_id']]
            amount_text, amount  = share_params['amount'] or ('',Decimal('0'))
            split_dict[user] = amount
            split_text_dict[user] = amount_text
        e.split(split_dict, split_text_dict)
        
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

    def delete(self, id):
        c.title = 'Delete an Expenditure'
        c.expenditure = meta.Session.query(model.Expenditure).get(id)
        if c.expenditure is None:
            abort(404)

        return render('/spend/delete.mako')

    @redirect_on_get('delete')
    @authenticate_form
    def destroy(self, id):
        e = meta.Session.query(model.Expenditure).get(id)
        if e is None:
            abort(404)

        if 'delete' in request.params:
            meta.Session.delete(e)

            meta.Session.commit()
            show = ("Expenditure of %s paid for by %s deleted." %
                    (e.amount, e.spender))
            h.flash(show)

            involved_users = set(sp.user for sp in e.splits if sp.share != 0)
            involved_users.add(e.spender)
            body = render('/emails/expenditure.txt',
                          extra_vars={'expenditure': e,
                                      'op': 'deleted'})
            g.handle_notification(involved_users, show, body)

        return h.redirect_to('/')
