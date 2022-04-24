class LimObj:
    def __init__(self, lim_class):
        self.lim_class = lim_class
        self.fields = {}

    def __hash__(self):
        return hash(self.value)

    def __eq__(self, rhs):
        return self.value == rhs.value

class LimClass(LimObj):
    def __init__(self, name, parent_class, *args, prototype=None):
        super().__init__(*args)
        self.name = name
        self.parent_class = parent_class
        self.prototype = prototype or self.parent_class.prototype if self.parent_class else {}

    def define_method(self, method_name, method):
        if method_name in self.fields and self.fields[method_name].is_callable():
            method.parent = self.fields
        self.fields[method_name] = method

    def instanciate(self, value):
        obj = LimObj(self)
        obj.value = value
        obj.fields = {**self.prototype}
        return obj

class LimFunction(LimObj):
    def __init__(self, code, *args):
        super().__init__(*args)
        if isinstance(code, LimClass):
            breakpoint()
        self.code = code

    def __call__(self, *args, **kwargs):
        return self.code(*args, **kwargs)

class LimMethod(LimFunction):
    def __init__(self, this, *args):
        super().__init__(*args)
        self.this = this
        self.parent = None

    def __call__(self, *args):
        return super().__call__(self.this, *args)

class Code:
    pass

class NativeCode(Code):
    def __init__(self, function):
        self.function = function

    def __call__(self, *args, **kwargs):
        return self.function(*args, **kwargs)

class LimCode(Code):
    def __init__(self, ast):
        self.ast = ast

    def __call__(self, *args, **kwargs):
        return self.function(*args, **kwargs)

binops = {
    '+': '$add',
    '-': '$sub',
    '*': '$mul',
    '/': '$div',
}

class Scope:
    def __init__(self):
        self.builtins = {}
        self.file_scope = {}
        self.function_scope = {}
        self.init_builtins()

    def init_builtins(self):
        self.builtins = {}
        lim_type = LimClass("Type", None, None)
        lim_type.lim_class = lim_type
        lim_type.parent_class = lim_type
        self.builtins["Type"] = lim_type

        self.builtins["Struct"] = LimClass("Struct", lim_type, lim_type)
        self.builtins["Null"] = LimClass("Null", lim_type, lim_type)
        self.builtins["Function"] = LimClass("Function", lim_type, lim_type)
        self.builtins["Method"] = LimClass("Method", self.builtins["Function"], lim_type)
        self.builtins["Number"] = LimClass("Number", lim_type, lim_type)
        self.builtins["Integer"] = LimClass("Integer", self.builtins["Number"], lim_type)
        self.builtins["Float"] = LimClass("Float", self.builtins["Number"], lim_type)
        self.builtins["String"] = LimClass("String", lim_type, lim_type)
        self.builtins["Array"] = LimClass("Array", lim_type, lim_type)
        self.builtins["Dictionary"] = LimClass("Dictionary", lim_type, lim_type)

        self.builtins["null"] = LimObj(self.builtins["Null"])
        self.build_prototypes()

    def build_native_function(self, fn):
        return LimFunction(NativeCode(fn), self.builtins["Function"])

    def build_prototypes(self):
        self.builtins["Number"].prototype = {
            '$add': self.build_native_function(lambda x, y: x.value+y.value),
            '$sub': self.build_native_function(lambda x, y: x.value-y.value),
            '$mul': self.build_native_function(lambda x, y: x.value*y.value),
            '$div': self.build_native_function(lambda x, y: x.value/y.value),
            '$string': self.build_native_function(lambda x: x.value),
        }
        self.builtins["Integer"].prototype = self.builtins["Number"].prototype
        self.builtins["Float"].prototype = self.builtins["Number"].prototype
        self.builtins["Array"].prototype = {
            '$string': self.build_native_function(lambda x: str([item.fields["$string"](item) for item in x.value])),
            'push': self.build_native_function(lambda x, y: x.value.append(y)),
            '$getitem': self.build_native_function(lambda x, y: x.value[y.value]),
        }
        self.builtins["String"].prototype = {
            '$string': self.build_native_function(lambda x: x.value),
        }
        self.builtins["Dictionary"].prototype = {
            '$string': self.build_native_function(lambda x: str({ key.fields["$string"](key): value.fields["$string"](value) for key, value in x.value.items() })),
            '$getitem': self.build_native_function(lambda x, y: x.value[y]),
            '$setitem': self.build_native_function(lambda x, y, z: x.value.__setitem__(y, z)),
            '$delitem': self.build_native_function(lambda x, y: x.value.__delitem__(y)),
        }

    def __getitem__(self, name):
        return self.builtins.get(name) or self.file_scope.get(name) or self.function_scope.get(name)

    def __setitem__(self, name, value):
        if name in self.builtins:
            self.builtins[name] = value
        elif name in self.file_scope:
            self.file_scope[name] = value
        else:
            self.function_scope[name] = value

class Program:
    def __init__(self):
        self.scope = Scope()
        self.scope.builtins["print"] = LimFunction(NativeCode(self.print), self.scope["Function"])

    def run(self, ast):
        return self.stmt(ast)

    def binop(self, lhs, rhs, op):
        return self.build_lim_obj(self.getfield(lhs, binops[op])(rhs))

    def build_lim_obj(self, obj):
        if isinstance(obj, int):
            return self.scope["Integer"].instanciate(obj)
        if isinstance(obj, float):
            return self.scope["Float"].instanciate(obj)
        if isinstance(obj, str):
            return self.scope["String"].instanciate(obj)
        if isinstance(obj, list):
            return self.scope["Array"].instanciate([self.build_lim_obj(x) for x in obj])
        if isinstance(obj, dict):
            return self.scope["Dictionary"].instanciate({self.build_lim_obj(key): self.build_lim_obj(value) for key, value in obj.items() })
        raise ValueError()

    def getitem(self, obj, key):
        return self.getfield(obj, "$getitem")(key)

    def setitem(self, obj, key, value):
        return self.getfield(obj, "$setitem")(key, value)

    def delitem(self, obj, key):
        return self.getfield(obj, "$delitem")(key)

    def getfield(self, obj, field_name):
        if field_name not in obj.fields:
            raise ValueError(obj.lim_class.name, field_name)
        field = obj.fields[field_name]
        if isinstance(field, LimFunction):
            return LimMethod(obj, field.code, self.scope["Function"])
        return field

    def to_string(self, obj):
        return self.build_lim_obj(self.getfield(obj, "$string")())

    def print(self, arg):
        print(self.to_string(arg).value)
        return arg

    def parse_argument_list(self, argument_list):
        if len(argument_list) > 2:
            return [self.expr(argument_list[1]), *self.parse_argument_list(argument_list[2])]
        else:
            return [self.expr(argument_list[1])]

    def expr(self, ast):
        if ast[0] == 'binop':
            return self.binop(self.expr(ast[2]), self.expr(ast[3]), ast[1])
        elif ast[0] == 'number':
            return self.build_lim_obj(ast[1])
        elif ast[0] == 'name':
            return self.scope[ast[1]]
        elif ast[0] == 'grouped':
            return self.expr(ast[1])
        elif ast[0] == 'assign':
            value = self.expr(ast[3])
            self.scope[ast[1]] = value
            return value
        elif ast[0] == 'call_expression':
            arguments = self.parse_argument_list(ast[2])
            return self.scope[ast[1]](*arguments)
        elif ast[0] == 'string':
            return self.build_lim_obj(ast[1])
        else:
            raise ValueError(f"Unknown expression {ast[0]}")

    def stmt(self, ast):
        if ast[0] == 'program':
            return self.stmt(ast[1])
        elif ast[0] == 'statement_list':
            value = self.stmt(ast[1])
            if len(ast) > 2:
                value = self.stmt(ast[2])
            return value
        elif ast[0] == 'expression':
            return self.expr(ast[1])
        else:
            print(ast)
            raise ValueError(f"Unknown statement {ast[0]}")

from pprint import pprint
from ply.lex import lex
from ply.yacc import yacc

# All tokens must be named in advance.
tokens = ( 'PLUS', 'MINUS', 'TIMES', 'DIVIDE', 'LPAREN', 'RPAREN',
           'NAME', 'NUMBER', 'ASSIGN', 'NEWLINE', 'COMMA', 'STRINGLITERAL')

# Ignored characters
t_ignore = ' \t'

# Token matching rules are written as regexs
t_ASSIGN = r'\='
t_PLUS = r'\+'
t_COMMA = r','
t_MINUS = r'-'
t_TIMES = r'\*'
t_DIVIDE = r'/'
t_LPAREN = r'\('
t_RPAREN = r'\)'
t_NAME = r'[a-zA-Z_][a-zA-Z0-9_]*'

# A function can be used if there is an associated action.
# Write the matching regex in the docstring.
def t_NUMBER(t):
    r'(\d+\.\d+)|(\d+)'
    if '.' in t.value:
        t.value = float(t.value)
    else:
        t.value = int(t.value)
    return t

def t_STRINGLITERAL(t):
    r'(\'.+\')|(".+")'
    t.value = t.value[1:-1]
    return t

def t_NEWLINE(t):
    r'\n+'
    t.lexer.lineno += t.value.count('\n')
    return t

# Error handler for illegal characters
def t_error(t):
    print(f'Illegal character {t.value[0]!r}')
    t.lexer.skip(1)

# Build the lexer object
lexer = lex()
    
# --- Parser

def p_program(p):
    '''
    program : statement_list
    '''
    p[0] = ('program', p[1])

def p_statement_list_1(p):
    '''
    statement_list : statement
    '''
    p[0] = ('statement_list', p[1])

def p_statement_list_2(p):
    '''
    statement_list : statement NEWLINE statement_list
    '''
    p[0] = ('statement_list', p[1], p[3])

def p_statement_expression(p):
    '''
    statement : expression
    '''
    p[0] = ('expression', p[1])

def p_assign_expression(p):
    '''
    expression : NAME ASSIGN expression
    '''
    p[0] = ('assign', p[1], p[2], p[3])

def p_call_expression(p):
    '''
    expression : NAME LPAREN argument_list RPAREN
    '''
    p[0] = ('call_expression', p[1], p[3])

def p_argument_list_empty(p):
    '''
    argument_list :
    '''

def p_argument_list_1(p):
    '''
    argument_list : expression
    '''
    p[0] = ('argument_list', p[1])

def p_argument_list_2(p):
    '''
    argument_list : expression COMMA argument_list
    '''
    p[0] = ('argument_list', p[1], p[3])


def p_expression(p):
    '''
    expression : term PLUS term
               | term MINUS term
    '''
    p[0] = ('binop', p[2], p[1], p[3])

def p_expression_term(p):
    '''
    expression : term
    '''
    p[0] = p[1]

def p_term(p):
    '''
    term : factor TIMES factor
         | factor DIVIDE factor
    '''
    p[0] = ('binop', p[2], p[1], p[3])

def p_term_factor(p):
    '''
    term : factor
    '''
    p[0] = p[1]

def p_factor_number(p):
    '''
    factor : NUMBER
    '''
    p[0] = ('number', p[1])

def p_factor_string(p):
    '''
    factor : STRINGLITERAL
    '''
    p[0] = ('string', p[1])

def p_factor_name(p):
    '''
    factor : NAME
    '''
    p[0] = ('name', p[1])

def p_factor_unary(p):
    '''
    factor : PLUS factor
           | MINUS factor
    '''
    p[0] = ('unary', p[1], p[2])

def p_factor_grouped(p):
    '''
    factor : LPAREN expression RPAREN
    '''
    p[0] = ('grouped', p[2])

def p_error(p):
    print(p)
    print(f'Syntax error at {p.value!r}')

# Build the parser
parser = yacc()

# Parse an expression
ast = parser.parse('''x = "foo"
y = 'bar'
print(2.2+2*(2+2))
print('foo')''')

program = Program()
program.run(ast)
