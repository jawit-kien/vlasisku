#-*- coding:utf-8 -*-

import re
from bottle import response, request, abort
from contextlib import contextmanager


def tex2html(tex):
    """Turn most of the TeX used in jbovlaste into HTML.
    
    >>> tex2html('$x_1$ is $10^2$ examples of $x_{2}$.')
    'x<sub>1</sub> is 10<sup>2</sup> examples of x<sub>2</sub>.'
    """
    def f(m):
        t = []
        for x in m.group(1).split('='):
            x = x.replace('{', '').replace('}', '')
            x = x.replace('*', u'×'.encode('utf-8'))
            if '_' in x:
                t.append('%s<sub>%s</sub>' % tuple(x.split('_')[0:2]))
            elif '^' in x:
                t.append('%s<sup>%s</sup>' % tuple(x.split('^')[0:2]))
            else:
                t.append(x)
        return '='.join(t)
    return re.sub(r'\$(.+?)\$', f, tex)

def braces2links(text):
    """Turns {quoted words} into HTML links.
    
    >>> braces2links("See also {mupli}, {mu'u}.")
    'See also <a href="/mupli">mupli</a>, <a href="/mu\\'u">mu\\'u</a>.'
    """
    def f(m):
        return '<a href="/%s">%s</a>' % (m.group(1), m.group(1))
    return re.sub(r'\{(.+?)\}', f, text)


def etag(tag):
    """Decorator to add ETag handling to a callback."""
    def decorator(f):
        def wrapper(**kwargs):
            response.header['ETag'] = tag
            if request.environ.get('HTTP_IF_NONE_MATCH', None) == tag:
                abort(304)
                return
            return f(**kwargs)
        return wrapper
    return decorator


@contextmanager
def ignore(exc):
    """Context manager to ignore an exception."""
    try:
        yield
    except exc:
        pass


if __name__ == '__main__':
    import doctest
    doctest.testmod()

