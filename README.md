# WIP ALPHA NOT WORKING
# lim
A modern dynamic language
# Goals
- No wall between language features and user features
  - All natives should be completely patchable
  - New language constructs can be added by users simply
- Everything is an expression
- Very simple scope everything is either file scoped or function scoped without sharing with inner functions
  - Closures cannot exist
  - No variable shadowing, refering in a function to a variable defined in the file refers to the file variable
- few reserved keywords, for now no reserved keywords
- imports with functions calls
- All gates open language, do whatever you want, "consenting adults", but turned to 100
- No language-defined gotchas, all code should do exactly what you expect it to do
  - Maybe a strict mode to prevent builtins patching to keep the language predictable
- No for loop, all done with array methods
- Interface function patching, allows to add a method to all classes implementing a list of methods and fields
- No difference between struct fields and struct methods
- similar `this` to javascript, maybe

The current implementation is written in python, expect the slowest language possible.

 
# Types
Current types are Integer, Float, String, Array and Function. Dictionaries coming soon.
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
# function scoping
all variables are scoped to its closest enclosing function
```
global_variable = 1
my_func = () {
  my_func_variable = 2
  () {
    global_variable = 2 //no issues
    my_func_variable = 3 //breaks
    inner_vairable = 1
  }()
  inner_variable = 2 // defines a new variable
}
```