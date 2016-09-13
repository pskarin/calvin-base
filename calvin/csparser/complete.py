import re
import types

from calvin.actorstore.store import DocumentationStore
from calvin.csparser.parser import calvin_parse
import calvin.csparser.astnode as ast
import calvin.csparser.visitor as visitor

class Completion(object):
    """ Object handling completion requests

    If optional argument first_line_is_zero is True, lines will be counted as starting from zero,
    default is to counting lines from one.

    Before any meaningful queries can be carried out, 'set_source' must be called.

    The main usage is to call 'complete' with line number and column of the insertion point for completion.
    """

    RE_MODULE   = r'\s*[a-z][a-zA-Z0-9_]*\s*:\s*((?:[a-z][a-zA-Z0-9_]*)?)$'
    RE_ACTOR    = r'\s*[a-z][a-zA-Z0-9_]*\s*:\s*([a-z][a-zA-Z0-9_]*)\.((?:[A-Z][a-zA-Z0-9_]*)?)$'
    RE_OUTPORT  = r'\s*([a-z][a-zA-Z0-9_]*)\.((?:[a-z][a-zA-Z0-9_]*)?)$'
    RE_INPORT   = r'.*>\s*([a-z][a-zA-Z0-9_]*)\.((?:[a-z][a-zA-Z0-9_]*)?)$'
    RE_PORTPROP = r'\s*([a-z][a-zA-Z0-9_]*\.[a-z][a-zA-Z0-9_]*)\s*\((?:[^,]+,)*\s*$'

    def __init__(self, first_line_is_zero=False):
        super(Completion, self).__init__()
        self._first_line_is_zero = first_line_is_zero
        self.finder = Finder()
        self.set_source('')
        self._init_metadata()

    def _init_metadata(self):
        def gather_actors(module):
            # Depth first
            l = []
            for m in d.modules(module):
                l = l + gather_actors(m)
            actors = d.actors(module)
            if module:
                # Add namespace
                actors = ['.'.join([module, a]) for a in actors]
            return l + actors

        d = DocumentationStore()
        metadata = {}
        actors = gather_actors('')

        for actor in actors:
            parts = actor.split('.')
            x = metadata
            for p in parts[:-1]:
                x = x.setdefault(p, {})
            x[parts[-1]] = d.metadata(actor)

        self.metadata = metadata

    def metadata_for(self, qualified_name):
        parts = qualified_name.split('.')
        x = self.metadata
        for p in parts:
            x = x.get(p, {})
        return x

    def current_context(self):
        # Find the last node
        n = self.tree
        if not n:
            return
        while n.children:
            n = n.children[-1]
        while type(n) is not ast.Block:
            n = n.parent
        return n

    def definition_for(self, name):
        context = self.current_context()
        query = lambda node: type(node) is ast.Assignment and node.ident == name
        defs = self.finder.find_all(context, query, maxdepth=2)
        if not defs:
            return
        return defs[0].actor_type

    def set_source(self, source):
        """Set the source text to operate on"""
        self.source = source
        self.source_lines = source.split('\n')

    @property
    def tree(self):
        """Parse code up to, but not including, the current line"""
        lineno = self.lineno if self._first_line_is_zero else self.lineno - 1
        src = "\n".join(self.source_lines[:lineno])
        ir, issues = calvin_parse(src)
        return ir

    def source_line(self, lineno):
        lineno = lineno if self._first_line_is_zero else lineno - 1
        if lineno < 0 or lineno >= len(self.source_lines):
            return ''
        return self.source_lines[lineno]

    def complete(self, lineno, col):
        """ Return tuple with ([<suggestions>], [<completions>])

        Suggestions the full text items that applies, whereas completions are the
        remaining parts of already partially typed text items.

        Example: Typing 'io.P' and calling complete with lineno=1 and col=4 returns (['Print], ['rint'])
        """
        self.lineno = lineno
        self.col = col
        line = self.source_line(self.lineno)
        line, suffix = line[:col], line[col:]

        completions = [
            (self.RE_MODULE, self._complete_module),
            (self.RE_ACTOR, self._complete_actor),
            (self.RE_OUTPORT, self._complete_outport),
            (self.RE_INPORT, self._complete_inport),
            (self.RE_PORTPROP, self._complete_portprop),
        ]

        for regex, handler in completions:
            m = re.match(regex, line)
            if m:
                return handler(m)

        return [], []

    def _filter_partial(self, items, partial):
        start = len(partial)
        matches = [x for x in items if x.startswith(partial)]
        completions = [x[start:] for x in matches]
        return matches, completions

    def _complete_module(self, matched):
        partial = matched.group(1) or ''
        modules = self.metadata.keys()
        return self._filter_partial(modules, partial)

    def _complete_actor(self, matched):
        module = matched.group(1)
        partial = matched.group(2) or ''
        actors = self.metadata.get(module, []).keys()
        return self._filter_partial(actors, partial)

    def _complete_port(self, matched, what):
        name = matched.group(1)
        partial = matched.group(2) or ''
        # 1. Match name with actor type, need to find relevant assignments
        actor_type = self.definition_for(name)
        if not actor_type:
            return [], []
        # 2. Get inports from actor metadata
        md = self.metadata_for(actor_type)
        ports = md.get(what, [])
        return self._filter_partial(ports, partial)

    def _complete_outport(self, matched):
        return self._complete_port(matched, 'outputs')

    def _complete_inport(self, matched):
        return self._complete_port(matched, 'inputs')

    def _complete_portprop(self, matched):
        port = matched.group(1) or ''
        # FIXME
        return port

#
#  Use this as generic finder and add to ast.py
#
class Finder(object):
    """
    Perform queries on AST
    """
    def __init__(self):
        super(Finder, self).__init__()

    @visitor.on('node')
    def visit(self, node):
        pass

    @visitor.when(ast.Node)
    def visit(self, node):
        if self.query(node):
            self.matches.append(node)
        descend = not node.is_leaf() and self.depth < self.maxdepth
        if descend:
            self.depth += 1
            map(self.visit, node.children)
            self.depth -= 1

    def find_all(self, root, query, maxdepth=1024):
        """
        Return a list of all nodes matching <kind>, at most <maxdepth> levels
        down from the starting node <node>
        If root evaluates to False or is not a subclass of ast.Node, return None

        """
        self.depth = 0
        self.maxdepth = maxdepth
        self.query = query
        self.matches = []
        if root and isinstance(root, ast.Node):
            self.visit(root)
        return self.matches


if __name__ == '__main__':

    import pytest
    import unittest
    import inspect
    from test import test_support

    class TestBase(unittest.TestCase):

        source_text = """
        component Foo() a -> b {
            flt : std.Identity()
            .a > flt.in
            flt.out > .b
        }
        src:std.Counter()
        snk:io.Print()

        src.integer > snk.token
        """

        def setUp(self):
            completion = Completion()
            completion.set_source(inspect.cleandoc(self.source_text))
            self.completion = completion

        def tearDown(self):
            pass

    class SanityCheck(TestBase):

        def test_sanity(self):
            completion = self.completion
            self.assertTrue(completion.metadata)
            self.assertTrue(completion.source)
            self.assertEqual(completion.source_lines[6], 'snk:io.Print()')
            self.assertEqual(completion.source_line(7), 'snk:io.Print()')
            completion._first_line_is_zero = True
            self.assertEqual(completion.source_lines[6], 'snk:io.Print()')
            self.assertEqual(completion.source_line(6), 'snk:io.Print()')


    class ActorCompletionTests(TestBase):

        def test_completion_module(self):
            suggestion, _ = self.completion.complete(7, 4)
            self.assertEqual(set(suggestion), set(self.completion.metadata.keys()))

        def test_completion_module_partial(self):
            suggestion, completion = self.completion.complete(7, 5)
            self.assertEqual(set(suggestion), set(['io']))
            self.assertEqual(set(completion), set(['o']))

        def test_completion_module_partial2(self):
            suggestion, completion = self.completion.complete(6, 5)
            self.assertEqual(set(suggestion), set(['std', 'sensor']))
            self.assertEqual(set(completion), set(['td', 'ensor']))

        def test_completion_actor(self):
            suggestion, completion = self.completion.complete(6, 8)
            expected = self.completion.metadata['std'].keys()
            self.assertEqual(set(suggestion), set(expected))
            self.assertEqual(set(completion), set(expected))

        def test_completion_actor_partial(self):
            suggestion, completion = self.completion.complete(6, 10)
            expected = [x for x in self.completion.metadata['std'].keys() if x.startswith('Co')]
            self.assertEqual(set(suggestion), set(expected))
            self.assertEqual(set(completion), set([x[2:] for x in expected]))

    class PortCompletionTests(TestBase):

        def test_outport(self):
            suggestion, completion = self.completion.complete(9, 4)
            self.assertEqual(set(suggestion), set(['integer']))
            self.assertEqual(set(completion), set(['integer']))

        def test_outport_partial(self):
            suggestion, completion = self.completion.complete(9, 6)
            self.assertEqual(set(suggestion), set(['integer']))
            self.assertEqual(set(completion), set(['teger']))

        def test_inport(self):
            suggestion, completion = self.completion.complete(9, 18)
            self.assertEqual(set(suggestion), set(['token']))
            self.assertEqual(set(completion), set(['token']))


        def test_inport_partial(self):
            suggestion, completion = self.completion.complete(9, 20)
            self.assertEqual(set(suggestion), set(['token']))
            self.assertEqual(set(completion), set(['ken']))

    class PortCompletionIncompleteSourceTests(PortCompletionTests):

        def setUp(self):
            super(PortCompletionIncompleteSourceTests, self).setUp()
            # Patch complete to truncate the source code
            cmpl = self.completion.complete
            def complete_trunc(self, lineno, col):
                if not self._first_line_is_zero:
                    lineno = lineno - 1
                src_lines = self.source_lines[:lineno - 1] + [self.source_lines[lineno][:col]]
                src = "\n".join(src_lines)
                self.set_source(src)
                return cmpl(lineno, col)

            self.completion.complete = types.MethodType(complete_trunc, self.completion, Completion)



    class PortPropertyCompletionTests(TestBase):

        @unittest.expectedFailure
        def test_outport(self):
            self.assertTrue(False)

    class NoCompletions(TestBase):

        def test_completion_module(self):
            suggestion, _ = self.completion.complete(1, 3)
            self.assertEqual(set(suggestion), set([]))

    def test_main():
        test_support.run_unittest(
            SanityCheck,
            ActorCompletionTests,
            PortCompletionTests,
            PortPropertyCompletionTests,
            NoCompletions,
            PortCompletionIncompleteSourceTests,
        )

    try:
        test_main()
    except:
        pass
