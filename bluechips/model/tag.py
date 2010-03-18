from bluechips.model import meta

class Tag(object):
    def __init__(self, name=u""):
        self.name = name

    def __repr__(self):
        return '<Tag: name: %s>' % (self.name)

def create_tag(name):
    if not isinstance(name, unicode):
        raise TypeError('%r is not a unicode object' % type(name).__name__)
    t = meta.Session.query(Tag).filter_by(name=name).first()
    if t is None:
        t = Tag(name)

    return t


__all__ = ['Tag']
