from types import Currency

class Split(object):
    def __init__(self, expenditure=None, user=None, share=Currency(0), share_text=u""):
        self.expenditure = expenditure
        self.user = user
        self.share = share
        self.share_text = share_text

    def __repr__(self):
        return '<Split: expense: %s user: %s share: %s>' % (self.expenditure,
                                                            self.user,
                                                            self.share)

__all__ = ['Split']
