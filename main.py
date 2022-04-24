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
    def __init__(self, ast, program):
        self.ast = ast
        self.program = program

    def __call__(self, *args, **kwargs):
        self.program.scope.in_function = True
        self.program.scope.function_scopes.append({})
        value = self.program.stmt(self.ast)
        self.program.scope.function_scopes.pop()
        self.program.scope.in_function = False
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
        self.in_function = False

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
            '$string': self.build_native_function(lambda x: str([item.fields["$string"](item) for item in x.value])),
            'push': self.build_native_function(lambda x, y: x.value.append(y)),
            '$getitem': self.build_native_function(lambda x, y: x.value[y.value]),
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
        value = self.builtins.get(name) or self.file_scope.get(name) or self.in_function and self.function_scopes[-1].get(name)
        if value is False or value is None:
            raise KeyError(f"Cannot find '{name}' in scope")
        return value

    def __setitem__(self, name, value):
        if name in self.builtins:
            self.builtins[name] = value
        elif name in self.file_scope or not self.in_function:
            self.file_scope[name] = value
        else:
            self.function_scopes[-1][name] = value

    def __contains__(self, name):
        return name in self.builtins or name in self.file_scope or self.in_function and name in self.function_scopes[-1]

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
            return self.scope["Array"].instanciate([self.build_lim_obj(x) for x in obj])
        if isinstance(obj, dict):
            return self.scope["Dictionary"].instanciate({self.build_lim_obj(key): self.build_lim_obj(value) for key, value in obj.items() })
        raise ValueError(obj)

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
        return self.getfield(obj, "$string")()

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
            arguments = self.parse_argument_list(ast[2]) if ast[2] else []
            return self.expr(ast[1])(*arguments)
        elif ast[0] == 'string':
            return self.build_lim_obj(ast[1])
        elif ast[0] == 'access':
            return self.getfield(self.expr(ast[1]), ast[2])
        elif ast[0] == 'function_definition':
            return LimFunction(LimCode(ast[1], self), self.scope["Function"])
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


if __name__ == '__main__':
    with open(sys.argv[1], 'r') as f:
        text = f.read()

    Program(text).run()
