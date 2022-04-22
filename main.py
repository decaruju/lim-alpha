

class LimObj:
    def __init__(self, lim_class):
        self.lim_class = lim_class
        self.fields = {}

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

function_prototype = {
}

def lim_print(obj, scope):
    return build_lim_obj(obj.fields['$string'](obj), scope)

binops = {
    '+': '$add',
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

        self.builtins["null"] = LimObj(self.builtins["Null"])
        self.build_prototypes()

    def build_prototypes(self):
        self.builtins["Number"].prototype = {
            '$add': LimFunction(NativeCode(lambda x, y: x.value+y.value), self.builtins["Function"]),
            '$string': LimFunction(NativeCode(lambda x: str(x.value)), self.builtins["Function"]),
        }
        self.builtins["Integer"].prototype = {
            '$add': LimFunction(NativeCode(lambda x, y: x.value+y.value), self.builtins["Function"]),
            '$string': LimFunction(NativeCode(lambda x: str(x.value)), self.builtins["Function"]),
        }
        self.builtins["Float"].prototype = {
            '$add': LimFunction(NativeCode(lambda x, y: x.value+y.value), self.builtins["Function"]),
            '$string': LimFunction(NativeCode(lambda x: str(x.value)), self.builtins["Function"]),
        }
        self.builtins["Function"].prototype = function_prototype


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

    def run(self):
        three = self.build_lim_obj(3)
        four = self.build_lim_obj(4)
        seven = self.binop(three, four, '+')
        self.scope['print'](seven)

    def binop(self, lhs, rhs, op):
        return self.build_lim_obj(self.getfield(lhs, binops[op])(rhs))

    def build_lim_obj(self, obj):
        if isinstance(obj, int):
            return self.scope["Integer"].instanciate(obj)

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
        print(self.to_string(arg))
        return arg

program = Program()
program.run()
