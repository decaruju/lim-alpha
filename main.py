from parser import parser
import sys

class LimObj:
    def __init__(self, lim_class):
        self.lim_class = lim_class
        self.fields = {}

    def __repr__(self):
        return "LimObj" + str(getattr(self, 'value', ''))

    def __hash__(self):
        return hash(self.value)

    def __eq__(self, rhs):
        if isinstance(rhs, LimObj):
            return self.value == rhs.value
        return self.value == rhs

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
        if self.fields.get('$prototype'):
            obj.fields = self.fields.get('$prototype').value
        else:
            obj.fields = self.prototype

        return obj

def call_function(func, *args):
    # if isinstance(func.code, LimCode) and isinstance(func, LimMethod):
    #     func.code.args.insert(0, 'this')
    this_added = False
    if func.lim_class.name == 'Method':
        args = [func.this, *args]
        if isinstance(func.value, LimCode):
            func.value.args.insert(0, 'this')
            this_added = True
    value = func.value(*args)
    if this_added:
        func.value.args.pop(0)
    return value

class Code:
    pass

class NativeCode(Code):
    def __init__(self, function):
        self.function = function

    def __call__(self, *args, **kwargs):
        return self.function(*args, **kwargs)

class LimCode(Code):
    def __init__(self, ast, program, args):
        self.ast = ast
        self.program = program
        self.args = args

    def __call__(self, *args, **kwargs):
        old_function_scopes = self.program.scope.function_scopes
        self.program.scope.function_scopes = [*self.scopes]
        self.program.scope.function_scopes.append({arg_name: arg_value for arg_name, arg_value in zip(self.args, args)})
        value = self.program.stmt(self.ast)
        self.program.scope.function_scopes = old_function_scopes
        return value

binops = {
    '+': '$add',
    '-': '$sub',
    '*': '$mul',
    '/': '$div',
}

class Scope:
    def __init__(self, program):
        self.program = program
        self.builtins = {}
        self.file_scope = {}
        self.function_scopes = []
        self.init_builtins()

    def init_builtins(self):
        self.builtins = {}
        lim_type = LimClass("Type", None, None)
        lim_type.lim_class = lim_type
        lim_type.parent_class = lim_type
        self.builtins["Type"] = lim_type

        self.builtins["Struct"] = LimClass("Struct", lim_type, lim_type)
        self.builtins["Null"] = LimClass("Null", lim_type, lim_type)
        self.builtins["Bool"] = LimClass("Bool", lim_type, lim_type)
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
        self.build_constants()

    def build_native_function(self, fn):
        return self.builtins["Function"].instanciate(NativeCode(lambda *arg: self.program.build_lim_obj(fn(*arg))))

    def array_to_string(self, array):
        elements = ', '.join([self.program.to_string(item).value for item in array.value])
        return f'[{elements}]'

    def build_prototypes(self):
        self.builtins["Function"].prototype = {
            '$call': self.build_native_function(call_function),
            '$string': self.build_native_function(lambda x: 'LimFunction'),
        }
        self.builtins["Type"].prototype = {
            '$string': self.build_native_function(lambda x: x.name),
        }
        self.builtins["Method"].prototype = { **self.builtins["Function"].prototype }
        self.builtins["Number"].prototype = {
            '$add': self.build_native_function(lambda x, y: x.value+y.value),
            '$sub': self.build_native_function(lambda x, y: x.value-y.value),
            '$mul': self.build_native_function(lambda x, y: x.value*y.value),
            '$div': self.build_native_function(lambda x, y: x.value/y.value),
            '$string': self.build_native_function(lambda x: str(x.value)),
            '$bool': self.build_native_function(lambda x: True)
        }
        self.builtins["Integer"].prototype = self.builtins["Number"].prototype
        self.builtins["Float"].prototype = self.builtins["Number"].prototype
        self.builtins["Array"].prototype = {
            '$string': self.build_native_function(self.array_to_string),
            'push': self.build_native_function(lambda x, y: x.value.append(y)),
            '$getitem': self.build_native_function(lambda x, y: x.value[y.value]),
            '$each': self.build_native_function(lambda x, y: [self.program.call(y, i) for i in x.value] and x)
        }
        self.builtins["String"].prototype = {
            '$string': self.build_native_function(lambda x: x.value),
            '$add': self.build_native_function(lambda x, y: x.value + self.program.to_string(y).value)
        }
        self.builtins["Null"].prototype = {
            '$string': self.build_native_function(lambda x: "null"),
        }
        self.builtins["Bool"].prototype = {
            '$string': self.build_native_function(lambda x: str(x.value)),
            '$bool': self.build_native_function(lambda x: x),
        }
        self.builtins["Dictionary"].prototype = {
            '$string': self.build_native_function(lambda x: str({ self.program.to_string(key).value: self.program.to_string(value).value for key, value in x.value.items() })),
            '$getitem': self.build_native_function(lambda x, y: x.value[y]),
            '$setitem': self.build_native_function(lambda x, y, z: x.value.__setitem__(y, z)),
            '$delitem': self.build_native_function(lambda x, y: x.value.__delitem__(y)),
        }

    def build_constants(self):
        self.builtins['null'] = self.builtins['Null'].instanciate(None)
        self.builtins['true'] = self.builtins['Bool'].instanciate(True)
        self.builtins['false'] = self.builtins['Bool'].instanciate(False)

    def set_prototypes(self):
        for builtin in self.builtins.values():
            if isinstance(builtin, LimClass):
                builtin.prototype['$class'] = builtin
                builtin.fields['$prototype'] = self.program.build_lim_obj({ self.program.build_lim_obj(key): value for key, value in self.program.build_lim_obj(builtin.prototype).value.items() })

    def __getitem__(self, name):
        for scope in [self.builtins, self.file_scope, *self.function_scopes]:
            if name in scope:
                return scope[name]
        raise KeyError(f"Cannot find '{name}' in scope")

    def __setitem__(self, name, value):
        for scope in [self.builtins, self.file_scope, *self.function_scopes]:
            if name in scope:
                scope[name] = value
                break
        else:
            if self.function_scopes:
                self.function_scopes[-1][name] = value
            else:
                self.file_scope[name] = value
        return value

    def __contains__(self, name):
        return name in self.builtins or name in self.file_scope or self.function_scopes and name in self.function_scopes[-1]

class Program:
    def __init__(self):
        self.scope = Scope(self)
        self.scope.set_prototypes()
        self.scope.builtins["print"] = self.scope['Function'].instanciate(NativeCode(self.print))

    def run(self, text):
        self.ast = parser.parse(text)
        return self.stmt(self.ast)

    def binop(self, lhs, rhs, op):
        return self.call(self.getfield(lhs, binops[op]), rhs)

    def build_lim_obj(self, obj):
        if isinstance(obj, int):
            return self.scope["Integer"].instanciate(obj)
        if isinstance(obj, float):
            return self.scope["Float"].instanciate(obj)
        if isinstance(obj, str):
            return self.scope["String"].instanciate(obj)
        if isinstance(obj, list):
            return self.scope["Array"].instanciate(obj)
        if obj is None:
            return self.scope["Null"].instanciate(obj)
        if isinstance(obj, dict):
            return self.scope["Dictionary"].instanciate({self.build_lim_obj(key): self.build_lim_obj(value) for key, value in obj.items() })
        if isinstance(obj, LimObj):
            return obj
        raise ValueError(f'Cannot build lim object {obj}')

    def getitem(self, obj, key):
        return self.getfield(obj, "$getitem")(key)

    def setitem(self, obj, key, value):
        return self.getfield(obj, "$setitem")(key, value)

    def delitem(self, obj, key):
        return self.getfield(obj, "$delitem")(key)

    def setfield(self, obj, field_name, value):
        obj.fields[field_name] = value
        return value

    def call(self, obj, *args):
        return self.getfield(obj, '$call').value(obj, *args)

    def getfield(self, obj, field_name):
        if field_name not in obj.fields:
            if field_name in obj.lim_class.fields['$prototype'].value:
                field = obj.lim_class.fields['$prototype'].value[field_name]
            else:
                breakpoint()
                raise ValueError(obj.lim_class.name, field_name)
        else:
            field = obj.fields[field_name]
        if field.lim_class.name == 'Function':
            method = self.scope['Method'].instanciate(field.value)
            method.this = obj
            return method
        return field

    def to_string(self, obj):
        return self.call(self.getfield(obj, "$string"))

    def to_bool(self, obj):
        return self.call(self.getfield(obj, "$bool"))

    def print(self, arg):
        print(self.to_string(arg).value)
        return arg

    def parse_argument_list(self, argument_list):
        if len(argument_list) > 2:
            return [self.expr(argument_list[1]), *self.parse_argument_list(argument_list[2])]
        else:
            return [self.expr(argument_list[1])]

    def build_array(self, ast):
        if len(ast) == 1:
            return []
        elif len(ast) == 2:
            return [ast[1]]
        else:
            return [ast[1], *self.build_array(ast[2])]

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
            arguments = [self.expr(x) for x in self.build_array(ast[2])]
            return self.call(self.expr(ast[1]), *arguments)
        elif ast[0] == 'string':
            return self.build_lim_obj(ast[1])
        elif ast[0] == 'access':
            return self.getfield(self.expr(ast[1]), ast[2])
        elif ast[0] == 'assign_member':
            return self.setfield(self.expr(ast[1]), ast[2], self.expr(ast[3]))
        elif ast[0] == 'index':
            return self.call(self.getfield(self.expr(ast[1]), '$getitem'), self.expr(ast[2]))
        elif ast[0] == 'assign_index':
            return self.call(self.getfield(self.expr(ast[1]), '$setitem'), self.expr(ast[2]), self.expr(ast[3]))
        elif ast[0] == 'function_definition':
            function = self.scope['Function'].instanciate(LimCode(ast[2], self, self.build_array(ast[1])))
            function.value.scopes = [*self.scope.function_scopes]
            return function
        elif ast[0] == 'array_expression':
            return self.build_lim_obj(self.expr(ast[1]))
        elif ast[0] == 'array_content':
            return [self.expr(x) for x in self.build_array(ast)]
        elif ast[0] == 'dictionary_expression':
            return self.build_lim_obj(self.expr(ast[1]))
        elif ast[0] == 'dictionary_content':
            return {self.expr(elem[0]): self.expr(elem[1]) for elem in self.build_array(ast)}
        elif ast[0] == 'if_expression':
            if_clause = ast[1]
            if self.to_bool(self.expr(if_clause[1])).value:
                return self.stmt(if_clause[2])
            else_if_clause = ast[2]
            while True:
                if len(else_if_clause) > 1:
                    if self.to_bool(self.expr(else_if_clause[1][1])).value:
                        return self.stmt(else_if_clause[1][2])
                    elif len(else_if_clause) > 2:
                        else_if_clause = else_if_clause[2]
                    else:
                        break
                else:
                    break
            else_clause = ast[3]
            if len(else_clause) > 1:
                return self.stmt(else_clause[1])
            return self.scope['null']

        else:
            raise ValueError(f"Unknown expression {ast[0]}")

    def stmt(self, ast):
        if ast[0] == 'program':
            return self.stmt(ast[1])
        elif ast[0] == 'statement_list':
            if len(ast) == 1:
                return self.scope["Null"].instanciate(None)
            value = self.stmt(ast[1])
            if len(ast) > 2 and len(ast[2]) > 1:
                value = self.stmt(ast[2])
            return value
        elif ast[0] == 'expression':
            return self.expr(ast[1])
        else:
            raise ValueError(f"Unknown statement {ast[0]!r}")

program = Program()

if __name__ == '__main__':
    with open(sys.argv[1], 'r') as f:
        text = f.read()

    text = '\n'.join(clean_line for line in text.split("\n") if (clean_line := line.strip()))

    program.run(text)
