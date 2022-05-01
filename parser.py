from ply.lex import lex
from ply.yacc import yacc

reserved = {
    'if': 'IF',
    'else': 'ELSE',
    'elseif': 'ELSEIF',
}

tokens = ( 'PLUS', 'MINUS', 'TIMES', 'DIVIDE', 'LPAREN', 'RPAREN',
           'NAME', 'NUMBER', 'ASSIGN', 'NEWLINE', 'COMMA', 'STRINGLITERAL',
           'PERIOD', 'LBRACE', 'RBRACE', 'LBRACKET', 'RBRACKET', 'COLON',
           *reserved.values())

# Ignored characters
t_ignore = ' \t'

# Token matching rules are written as regexs
t_ASSIGN = r'\='
t_PLUS = r'\+'
t_PERIOD = r'\.'
t_COMMA = r','
t_IF = r'if'
t_MINUS = r'-'
t_TIMES = r'\*'
t_COLON = r'\:'
t_DIVIDE = r'/'
t_LPAREN = r'\('
t_RPAREN = r'\)'
t_LBRACE = r'\{'
t_RBRACE = r'\}'
t_LBRACKET = r'\['
t_RBRACKET = r'\]'

# A function can be used if there is an associated action.
# Write the matching regex in the docstring.

def t_NAME(t):
    r'[a-zA-Z\$_][a-zA-Z0-9\$_]*'
    if t.value in reserved:
        t.type = reserved[t.value]
    return t

def t_NUMBER(t):
    r'(\d+\.\d+)|(\d+)'
    if '.' in t.value:
        t.value = float(t.value)
    else:
        t.value = int(t.value)
    return t

def t_STRINGLITERAL(t):
    r'(\'(\\.|[^\'\\])*\')|("(\\.|[^"\\])*")'
    t.value = t.value[1:-1]
    return t

def t_NEWLINE(t):
    r'\n+'
    t.lexer.lineno += t.value.count('\n')
    return t

# Error handler for illegal characters
def t_error(t):
    print(f'Illegal character {t.value[0]!r}')

# Build the lexer object
lexer = lex()
    
# --- Parser

def p_program(p):
    '''
    program : statement_list
    '''
    print('in')
    p[0] = ('program', p[1])

def p_statement_list_newline(p):
    '''
    statement_list : NEWLINE statement_list
    '''
    p[0] = p[2]

def p_statement_list_newline_after(p):
    '''
    statement_list : statement_list NEWLINE
    '''
    p[0] = p[1]

def p_statement_list_1(p):
    '''
    statement_list : statement
    '''
    p[0] = ('statement_list', p[1])

def p_statement_list_0(p):
    '''
    statement_list :
    '''
    p[0] = ('statement_list', )

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

def p_function_definition_expression(p):
    '''
    expression : LPAREN argument_definitions RPAREN LBRACE statement_list RBRACE
    '''
    p[0] = ('function_definition', p[2], p[5])

def p_argument_definitions_empty(p):
    '''
    argument_definitions :
    '''
    p[0] = ('argument_definitions', )

def p_argument_definitions_one(p):
    '''
    argument_definitions : NAME
    '''
    p[0] = ('argument_definitions', p[1])

def p_argument_definitions_multi(p):
    '''
    argument_definitions : NAME COMMA argument_definitions
    '''
    p[0] = ('argument_definitions', p[1], p[3])

def p_if_expression(p):
    '''
    expression : if_clause else_if_clauses else_clause
    '''
    p[0] = ('if_expression', p[1], p[2], p[3])

def p_if_clause(p):
    '''
    if_clause : IF expression LBRACE statement_list RBRACE
    '''
    p[0] = ('if_clause', p[2], p[4])

def p_else_if_clauses_empty(p):
    '''
    else_if_clauses :
    '''
    p[0] = ('else_if_clauses', )


def p_else_if_clauses_many(p):
    '''
    else_if_clauses : else_if_clause else_if_clauses
    '''
    p[0] = ('else_if_clauses', p[1], p[2])

def p_else_if_clause(p):
    '''
    else_if_clause : ELSEIF expression LBRACE statement_list RBRACE
    '''
    p[0] = ('else_if_clause', p[2], p[4])

def p_else_clause_empty(p):
    '''
    else_clause :
    '''
    p[0] = ('else_clause', )

def p_else_clause(p):
    '''
    else_clause : ELSE LBRACE statement_list RBRACE
    '''
    p[0] = ('else_clause', p[3])


def p_assign_expression(p):
    '''
    expression : NAME ASSIGN expression
    '''
    p[0] = ('assign', p[1], p[2], p[3])

def p_index_expression(p):
    '''
    expression : expression LBRACKET expression RBRACKET
    '''
    p[0] = ('index', p[1], p[3])

def p_assign_index_expression(p):
    '''
    expression : expression LBRACKET expression RBRACKET ASSIGN expression
    '''
    p[0] = ('assign_index', p[1], p[3], p[6])


def p_access_expression(p):
    '''
    expression : expression PERIOD NAME
    '''
    p[0] = ('access', p[1], p[3])

def p_assign_member_expression(p):
    '''
    expression : expression PERIOD NAME ASSIGN expression
    '''
    p[0] = ('assign_member', p[1], p[3], p[5])

def p_call_expression(p):
    '''
    expression : expression LPAREN argument_list RPAREN
    '''
    p[0] = ('call_expression', p[1], p[3])

def p_argument_list_empty(p):
    '''
    argument_list :
    '''
    p[0] = ('argument_list', )

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

def p_dictionary_expression(p):
    '''
    expression : LBRACE dictionary_content RBRACE
    '''
    p[0] = ('dictionary_expression', p[2])

def p_dictionary_content_zero(p):
    '''
    dictionary_content :
    '''
    p[0] = ('dictionary_content', )

def p_dictionary_content_one(p):
    '''
    dictionary_content : expression COLON expression
    '''
    p[0] = ('dictionary_content', (p[1], p[3]))

def p_dictionary_content_multi(p):
    '''
    dictionary_content : expression COLON expression COMMA dictionary_content
    '''
    p[0] = ('dictionary_content', (p[1], p[3]), p[5])


def p_array_expression(p):
    '''
    expression : LBRACKET array_content RBRACKET
    '''
    p[0] = ('array_expression', p[2])

def p_array_content_empty(p):
    '''
    array_content :
    '''
    p[0] = ('array_content', )

def p_array_content_1(p):
    '''
    array_content : expression
    '''
    p[0] = ('array_content', p[1])

def p_array_content_2(p):
    '''
    array_content : expression COMMA array_content
    '''
    p[0] = ('array_content', p[1], p[3])


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
    print(f'Syntax error at {p!r}')

parser = yacc()
