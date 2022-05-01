# WIP ALPHA NOT WORKING
# lim
A modern dynamic language
# Goals
- No wall between language features and user features
  - All natives should be completely patchable
  - New language constructs can be added by users
- Everything is an expression
- Functions return the last line
- No variable shadowing, refering in a function to a variable defined in the file refers to the file variable
- few reserved keywords, for now no reserved keywords except `$`
- imports with functions calls
- All gates open language, do whatever you want, "consenting adults", but turned to 100
- No language-defined gotchas, all code should do exactly what you expect it to do
  - Maybe a strict mode to prevent builtins patching to keep the language predictable
- No for loop, all done with array methods
- Interface function patching, allows to add a method to all classes implementing a list of methods and fields
- No difference between struct fields and struct methods, a function on a struct binds `this` when accessed
- Result monad for error handling

The current implementation is written in python, expect the slowest language possible.
 
# Types
Current types are Integer, Float, String, Array and Function. Dictionaries coming soon, structs later.
Integers are BigInts, arbitrarely large.
Floats are double precision.
Strings support both double and single quotes.
functions return their last 
```
my_int = 1
my_float = 2.2
my_string = "hello world"
my_function = (to_print) {
  print(to_print)
}
my_function(my_string)
```

functions are defined as 
```
(a) {
 a + 1
}
```
```
() {
  10
}
```
functions without arguments can be defined with only braces, similar to ruby blocks
```
{10}
```
# Partial function application
Calling a function with $ as an argument defines a new function by currying the function
`foo($, bar)` is the same as `(arg1) { foo(arg1, bar) }`

Multiple arguments can be bound by using $1, $2, ...
`foo($1, bar, $2)` is the same as `(arg1, arg2) { foo(arg1, bar, arg2) }`

All binary operators are diadic and monadic functions repectively when called with one or no expression

`arr.reduce(+)` is the same as `arr.reduce((a, b) { a + b })`

`arr.map(+2)` is the same as `arr.map((a) { a + 2 })`

`[1, 2, 3].map(1/)` is the same as `arr.map((a) { 1/a })`

`++2` is parsed as `(a) { (b) { b+2 } }`, so no c-style variable incrementing. However x += 1 is an expression, so no issues.

$ is a reserved keyword which defines functions
`arr.map($.foo.bar())` is the same as `arr.map((item) { item.foo.bar() })`

[maybe] multiple $1, $2 used in an expression refer to multiple arguments, in order
`arr.reduce($1.foo($2))` is the same as `arr.reduce((a, b) { a.foo(b) })`

This kind of syntatic sugar can easily become overly sweet, but can also improve readabilty immensely in some cases.


# Blocks
"magic methods" are prefixed with `$`
```
MyClass = class {
  foo = 1
  
  $new() {
  }
  
  $string() {
    this.foo.$string()
  }
}
```

# unknown
Array unpacking, can't use the python *arr, as is it bound to the function definition `*arr` is the same as `(a) { a*arr }`.

while is a method on functions ?
```
class Function {
  while = (fn) {
    count().each({
      this().if(fn)
    })
  }
}

{ arr.length > 0 }.while({
  print(arr.pop())
})
```
