from parser import parser
import sys

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
        self.code = code

    def __call__(self, *args, **kwargs):
        return self.code(*args, **kwargs)

class LimMethod(LimFunction):
    def __init__(self, this, *args):
        super().__init__(*args)
        self.this = this
        if isinstance(self.code, LimCode):
            self.code.args.insert(0, 'this')
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
    def __init__(self, ast, program, args):
        self.ast = ast
        self.program = program
        self.args = args

    def __call__(self, *args, **kwargs):
        last_scope = self.program.scope.function_scopes[-1] if self.program.scope.function_scopes else {}
        self.program.scope.function_scopes.append({arg_name: arg_value for arg_name, arg_value in zip(self.args, args)})
        value = self.program.stmt(self.ast)
        self.program.scope.function_scopes.pop()
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
        return LimFunction(NativeCode(lambda *arg: self.program.build_lim_obj(fn(*arg))), self.builtins["Function"])

    def array_to_string(self, array):
        elements = ', '.join([item.fields["$string"](item).value for item in array.value])
        return f'[{elements}]'


    def build_prototypes(self):
        self.builtins["Number"].prototype = {
            '$add': self.build_native_function(lambda x, y: x.value+y.value),
            '$sub': self.build_native_function(lambda x, y: x.value-y.value),
            '$mul': self.build_native_function(lambda x, y: x.value*y.value),
            '$div': self.build_native_function(lambda x, y: x.value/y.value),
            '$string': self.build_native_function(lambda x: str(x.value)),
        }
        self.builtins["Integer"].prototype = self.builtins["Number"].prototype
        self.builtins["Float"].prototype = self.builtins["Number"].prototype
        self.builtins["Array"].prototype = {
            '$string': self.build_native_function(self.array_to_string),
            'push': self.build_native_function(lambda x, y: x.value.append(y)),
            '$getitem': self.build_native_function(lambda x, y: x.value[y.value]),
            '$each': self.build_native_function(lambda x, y: [y(i) for i in x.value] and x)
        }
        self.builtins["String"].prototype = {
            '$string': self.build_native_function(lambda x: x.value),
            '$add': self.build_native_function(lambda x, y: x.value + self.program.to_string(y).value)
        }
        self.builtins["Dictionary"].prototype = {
            '$string': self.build_native_function(lambda x: str({ key.fields["$string"](key): value.fields["$string"](value) for key, value in x.value.items() })),
            '$getitem': self.build_native_function(lambda x, y: x.value[y]),
            '$setitem': self.build_native_function(lambda x, y, z: x.value.__setitem__(y, z)),
            '$delitem': self.build_native_function(lambda x, y: x.value.__delitem__(y)),
        }

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
    def __init__(self, test):
        self.scope = Scope(self)
        self.scope.builtins["print"] = LimFunction(NativeCode(self.print), self.scope["Function"])
        self.ast = parser.parse(text)

    def run(self):
        return self.stmt(self.ast)

    def binop(self, lhs, rhs, op):
        return self.getfield(lhs, binops[op])(rhs)

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

    def getfield(self, obj, field_name):
        if field_name not in obj.fields:
            raise ValueError(obj.lim_class.name, field_name)
        field = obj.fields[field_name]
        if isinstance(field, LimFunction):
            return LimMethod(obj, field.code, self.scope["Function"])
        return field

    def to_string(self, obj):
        return self.getfield(obj, "$string")()

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
            return self.expr(ast[1])(*arguments)
        elif ast[0] == 'string':
            return self.build_lim_obj(ast[1])
        elif ast[0] == 'access':
            return self.getfield(self.expr(ast[1]), ast[2])
        elif ast[0] == 'assign_member':
            return self.setfield(self.expr(ast[1]), ast[2], self.expr(ast[3]))
        elif ast[0] == 'index':
            return self.getfield(self.expr(ast[1]), '$getitem')(self.expr(ast[2]))
        elif ast[0] == 'function_definition':
            return LimFunction(LimCode(ast[2], self, self.build_array(ast[1])), self.scope["Function"])
        elif ast[0] == 'array_expression':
            return self.build_lim_obj(self.expr(ast[1]))
        elif ast[0] == 'array_content':
            return [self.expr(x) for x in self.build_array(ast)]
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
            breakpoint()
            raise ValueError(f"Unknown statement {ast[0]}")


if __name__ == '__main__':
    with open(sys.argv[1], 'r') as f:
        text = f.read()

    Program(text).run()
