class Tag(object):
    def __init__(self, expenditure=None, tag=u""):
        self.expenditure = expenditure
        self.tag = tag

    def __repr__(self):
        return '<Tag: expense: %s value: %s>' % (self.expenditure,
                                                            self.tag)

__all__ = ['Tag']
