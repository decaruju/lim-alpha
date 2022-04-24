from ply.lex import lex
from ply.yacc import yacc

tokens = ( 'PLUS', 'MINUS', 'TIMES', 'DIVIDE', 'LPAREN', 'RPAREN',
           'NAME', 'NUMBER', 'ASSIGN', 'NEWLINE', 'COMMA', 'STRINGLITERAL',
           'PERIOD', 'LBRACE', 'RBRACE'
          )

# Ignored characters
t_ignore = ' \t'

# Token matching rules are written as regexs
t_ASSIGN = r'\='
t_PLUS = r'\+'
t_PERIOD = r'\.'
t_COMMA = r','
t_MINUS = r'-'
t_TIMES = r'\*'
t_DIVIDE = r'/'
t_LPAREN = r'\('
t_RPAREN = r'\)'
t_LBRACE = r'\{'
t_RBRACE = r'\}'
t_NAME = r'[a-zA-Z\$_][a-zA-Z0-9\$_]*'

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
    r'(\'[\s\S]+\')|("[\s\S]+")'
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
                   | statement NEWLINE
                   | NEWLINE statement
                   | NEWLINE statement NEWLINE
    '''
    statements = [a for a in p[1:] if a != '\n'][0]
    p[0] = ('statement_list', statements)

def p_statement_list_2(p):
    '''
    statement_list : statement NEWLINE statement_list
                   | NEWLINE statement NEWLINE statement_list
    '''
    p[0] = ('statement_list', *[a for a in p[1:] if a != '\n'])

def p_statement_expression(p):
    '''
    statement : expression
    '''
    p[0] = ('expression', p[1])

def p_function_definition_expression(p):
    '''
    expression : LPAREN RPAREN LBRACE statement_list RBRACE
    '''
    p[0] = ('function_definition', p[4])

def p_assign_expression(p):
    '''
    expression : NAME ASSIGN expression
    '''
    p[0] = ('assign', p[1], p[2], p[3])

def p_access_expression(p):
    '''
    expression : expression PERIOD NAME
    '''
    p[0] = ('access', p[1], p[3])

def p_call_expression(p):
    '''
    expression : expression LPAREN argument_list RPAREN
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
    expression : term PLUS expression
               | term MINUS expression
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

parser = yacc()
