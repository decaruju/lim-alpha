from pprint import pprint
from ply.lex import lex
from ply.yacc import yacc

# --- Tokenizer
class LimObj:
    def __init__(self, value):
        self.value = value

# All tokens must be named in advance.
tokens = ( 'PLUS', 'MINUS', 'TIMES', 'DIVIDE', 'LPAREN', 'RPAREN',
           'NAME', 'NUMBER', 'ASSIGN', 'NEWLINE', 'COMMA' )

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
    r'\d+'
    t.value = int(t.value)
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

# Write functions for each grammar rule which is
# specified in the docstring.
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
    # p is a sequence that represents rule contents.
    #
    # expression : term PLUS term
    #   p[0]     : p[1] p[2] p[3]
    # 
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
program = parser.parse('''x = 6
print(2+2*(2+2), 3)''')

operations = {
    '+': '__add__',
    '-': '__sub__',
    '*': '__mul__',
    '/': '__div__',
}

global_scope = {
    'print': print
}

scope = {
}

def parse_argument_list(argument_list):
    if len(argument_list) > 2:
        return [expr(argument_list[1]), *parse_argument_list(argument_list[2])]
    else:
        return [expr(argument_list[1])]
    

def expr(ast):
    if ast[0] == 'binop':
        operation = operations[ast[1]]
        return getattr(expr(ast[2]), operation)(expr(ast[3]))
    elif ast[0] == 'number':
        return ast[1]
    elif ast[0] == 'name':
        return scope[ast[1]]
    elif ast[0] == 'grouped':
        return expr(ast[1])
    elif ast[0] == 'assign':
        value = expr(ast[3])
        scope[ast[1]] = value
        return value
    elif ast[0] == 'call_expression':
        arguments = parse_argument_list(ast[2])
        return global_scope[ast[1]](*arguments)
    else:
        raise ValueError(f"Unknown expression {ast[0]}")

def stmt(ast):
    if ast[0] == 'program':
        return stmt(ast[1])
    elif ast[0] == 'statement_list':
        value = stmt(ast[1])
        if len(ast) > 2:
            value = stmt(ast[2])
        return value
    elif ast[0] == 'expression':
        return expr(ast[1])
    else:
        print(ast)
        raise ValueError(f"Unknown statement {ast[0]}")


print(program)
stmt(program)