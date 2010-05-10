#!/usr/bin/env python
#-*- coding:utf-8 -*-

from __future__ import with_statement

from bottle import route, request, redirect, response, abort, send_file
from utils import etag, ignore, compound2affixes, dameraulevenshtein
import dbpickler as db
from render import Render
from os.path import join, dirname
from simplejson import dumps
import re
from stemming.porter2 import stem


DEBUG = __name__ == '__main__'
render = Render(DEBUG)


@route('/')
@etag(db.etag, DEBUG)
def index():
    showgrid = 'showgrid' in request.GET
    if 'query' in request.GET:
        redirect(request.GET['query'])
        return
    types = (('gismu', 'Root words.'),
             ('cmavo', 'Particles.'),
             ('cmavo cluster', 'Particle combinations.'),
             ('lujvo', 'Compound words.'),
             ("fu'ivla", 'Loan words.'),
             ('experimental gismu', 'Non-standard root words.'),
             ('experimental cmavo', 'Non-standard particles.'),
             ('cmene', 'Names.'))
    classes = set(e.grammarclass for e in db.entries.itervalues()
                                 if e.grammarclass)
    scales = db.class_scales
    return render.html('index', locals())


@route('/(?P<filename>favicon\.ico)')
@route('/static/:filename#.+#')
def static(filename):
    send_file(filename, root=join(dirname(__file__), 'static'))


@route('/opensearch/')
def opensearch():
    response.content_type = 'application/xml'
    hostname = request.environ['HTTP_HOST']
    path = request.environ.get('REQUEST_URI', '/opensearch/')
    path = path.rpartition('opensearch/')[0]
    return render.xml('opensearch', locals())

@route('/suggest/:prefix#.*#')
def suggest(prefix):
    prefix = request.GET.get('q', prefix.replace('+', ' ')).decode('utf-8')
    suggestions = []
    types = []
    entries = (e for e in db.entries.iterkeys()
                 if e.startswith(prefix))
    glosses = (g.gloss for g in db.glosses
                       if g.gloss.startswith(prefix))
    classes = set(e.grammarclass for e in db.entries.itervalues()
                                 if e.grammarclass
                                 and e.grammarclass.startswith(prefix))
    for x in xrange(5):
        with ignore(StopIteration):
            suggestions.append(entries.next())
            types.append(db.entries[suggestions[-1]].type)
        with ignore(StopIteration):
            suggestions.append(glosses.next())
            types.append('gloss')
        with ignore(KeyError):
            suggestions.append(classes.pop())
            types.append('class')
    if 'q' in request.GET:
        return '\n'.join(suggestions)
    else:
        response.content_type = 'application/json'
        return dumps([prefix, suggestions, types])


@route('/json/:entry')
def json(entry):
    if entry in db.entries:
        entry = db.entries[entry]
        word = entry.word
        type = entry.type
        affixes = entry.affixes
        grammarclass = entry.grammarclass
        definition = entry.definition
        notes = entry.notes
        del entry
        return locals()


@route('/:query#.*#')
@etag(db.etag, DEBUG)
def query(query):
    showgrid = 'showgrid' in request.GET
    query = query.decode('utf-8').replace('+', ' ')
    querystem = stem(query.lower())
    matches = set()
    
    entry = db.entries.get(query, None)
    if entry:    
        matches.add(entry)
    
    glosses = [g for g in db.gloss_stems.get(querystem, [])
                 if g.entry not in matches]
    matches.update(g.entry for g in glosses)
    
    affix = [e for e in db.entries.itervalues()
               if e not in matches
               and query in e.searchaffixes]
    matches.update(affix)
    
    classes = [e for e in db.entries.itervalues()
                 if e.grammarclass == query
                 or e.grammarclass
                 and re.split(r'[0-9*]', e.grammarclass)[0] == query]
    matches.update(classes)
    
    types = [e for e in db.entries.itervalues()
               if e.type == query]
    matches.update(types)
    
    definitions = [e for e in db.definition_stems.get(querystem, [])
                     if e not in matches]
    matches.update(definitions)
    
    notes = [e for e in db.note_stems.get(querystem, [])
               if e not in matches]
    matches.update(notes)
    
    if not entry and len(matches) == 1:
        redirect(matches.pop())
        return
    
    sourcemetaphor = []
    unknownaffixes = None
    similar = None
    if not matches:
        try:
            sourcemetaphor = [[e for e in db.entries.itervalues()
                                 if a in e.searchaffixes].pop()
                                 for a in compound2affixes(query)
                                 if len(a) != 1]
        except IndexError:
            unknownaffixes = True
        
        similar = [e.word for e in db.entries.itervalues()
                          if e not in matches
                          and dameraulevenshtein(query, e.word) == 1]
        
        similar += [g.gloss for g in db.glosses
                            if g.entry not in matches
                            and g.gloss not in similar
                            and dameraulevenshtein(query, g.gloss) == 1]
    
    return render.html('query', locals())


if __name__ == '__main__':
    import bottle
    bottle.debug(True)
    bottle.run(port=8080, reloader=True)

