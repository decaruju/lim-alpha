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

function_prototype = {
}

def lim_print(obj, scope):
    return build_lim_obj(obj.fields['$string'](obj), scope)

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
        self.scope['three'] = self.build_lim_obj(3)
        self.scope['four']= self.build_lim_obj(4)
        self.scope['seven'] = self.binop(self.scope['three'], self.scope['four'], '/')
        self.scope['array'] = self.build_lim_obj([1, 2, 3])
        self.getfield(self.scope['array'], "push")(self.scope['four'])
        self.scope['print'](self.scope['seven'])
        self.scope['print'](self.scope['array'])
        self.scope['print'](self.getitem(self.scope['array'], self.scope['three']))
        self.scope['dictionary'] = self.build_lim_obj({'a': 1, 3: 'b'})
        self.scope['print'](self.scope['dictionary'])
        self.setitem(self.scope['dictionary'], self.scope['four'], self.scope['seven'])
        self.scope['print'](self.getitem(self.scope['dictionary'], self.scope['four']))
        self.scope['print'](self.scope['dictionary'])
        self.delitem(self.scope['dictionary'], self.scope['three'])
        self.scope['print'](self.scope['dictionary'])
        # self.scope['Obj'] = LimClass("Obj", self.scope[''])

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

program = Program()
program.run()
