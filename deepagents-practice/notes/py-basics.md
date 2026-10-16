# Python 语言基础

> 跨项目通用的语言知识 —— 换个库、换个项目照样用得上。
> 收录标准：反直觉的、踩过的、以后会再遇到的。
> 开记于 2026-10-13 ｜ 索引见 [`../knowledge_notes.md`](../knowledge_notes.md)

---

## 函数与工具定义

### 函数签名与类型注解

- **一句话结论**：`def echo(text: str) -> str:` 里的 `: str` 和 `-> str` 是**写给人和工具看的说明**，Python 运行时不会因为你传错类型就报错。
- **为什么**：框架会读取你的函数签名，自动生成"这个工具叫什么、要什么参数"的说明书交给模型。注解写得越准，模型越不容易调错。
- **示例**：

  ```python
  def add(a: int, b: int) -> int:
      return a + b

  print(add("1", "2"))   # 12 —— 不报错，但其实是字符串拼接
  ```

- **踩坑点**：注解不是强制校验。写错了照样能跑，但模型会**按注解理解**你的工具。

### 装饰器

- **一句话结论**：`@xxx` 开头的写法叫装饰器，它在函数定义完成后，**把函数替换成另一个对象**。
- **为什么**：`@tool` 把普通函数包装成"工具对象"，模型才能识别和调用它。被包装后，原函数藏在 `.func` 里。
- **示例**：

  ```python
  def deco(fn):
      def wrapper(*args, **kwargs):
          print("调用前")
          return fn(*args, **kwargs)
      return wrapper

  @deco
  def hello(name):
      return f"hi {name}"

  hello("小明")   # 会先打印"调用前"
  ```

- **踩坑点**：装饰之后 `hello` 已经不是原来那个函数了，`hello.__name__` 之类的行为都会变。

### docstring

- **一句话结论**：函数体第一行的三引号字符串是 docstring，它是**运行时可读取的说明文本**（存在 `fn.__doc__`）。
- **为什么**：工具框架会把 docstring 当作"这个工具是干什么的"描述交给模型 —— 模型正是靠它决定要不要调用你的工具。
- **示例**：

  ```python
  def greet(name: str) -> str:
      """向指定的人问好。"""
      return f"hi {name}"

  print(greet.__doc__)   # 向指定的人问好。
  ```

- **踩坑点**：docstring 必须写在函数体第一行才生效；写在别处只是普通字符串，`__doc__` 读不到。

---

## 类与对象

### 类与继承：`class` / `super()` / 覆盖方法

- **一句话结论**：`class 子类(父类):` 的意思是「子类拥有父类的一切，并且可以改写其中某几个方法」。
- **为什么**：库给你的类已经把「对话、流式、回调」一大堆逻辑写好了。你只缺一小块，继承过来**只补那一块**，其余全部白拿。
- **示例**：

  ```python
  class Animal:
      def __init__(self, name):
          self.name = name

      def speak(self):
          return "..."

  class Dog(Animal):
      def speak(self):              # 方法名和父类一样 = 覆盖
          return f"{self.name}: woof"

  d = Dog("旺财")
  print(d.speak())   # 旺财: woof  —— 用的是子类的版本
  print(d.name)      # 旺财       —— 父类的 __init__ 白拿
  ```

- **踩坑点**：子类想沿用父类的初始化，要写 `super().__init__(...)`。另外，方法名和父类一样是**覆盖**（替换），不是"两个都留着"。

### 类 vs 实例：`type(类)` 得到的是元类

- **一句话结论**：**类**是图纸，**实例**是照图纸造出来的东西。`类名(...)` 才创建实例；而 `type(某个类)` 问的是"这个类本身是用什么造的"，会得到**元类**（普通类得到 `type`，pydantic 模型得到 `ModelMetaclass`）。
- **为什么**：Python 里"类"本身也是对象，它的类型就是元类。想知道"这个对象是什么类型"，必须把**实例**传进去。
- **示例**：

  ```python
  class Dog:
      pass

  print(type(Dog))     # <class 'type'>           —— 问的是"类"本身
  print(type(Dog()))   # <class '__main__.Dog'>   —— 问的是实例，这才是你要的
  ```

- **踩坑点**：想确认"对象造出来了没有"，写成两步：`d = Dog(); print(type(d))`。

### `self`：实例方法的第一个参数

- **一句话结论**：定义在类里的方法，第一个参数必须写 `self`，它代表"正在被调用的那个对象"。
- **为什么**：`a.bark(x)` 实际上等价于 `Dog.bark(a, x)` —— Python 会**自动**把 `a` 塞成第一个参数。你不写 `self` 占位，后面的参数就全错位了。
- **示例**：

  ```python
  class Dog:
      def __init__(self, name):
          self.name = name       # self 就是正在被创建的那个对象

      def bark(self):            # 少了 self 就会报错
          return f"{self.name}: woof"

  d = Dog("旺财")
  print(d.bark())                # 旺财: woof
  ```

- **踩坑点**：报错说 **"takes 0 positional arguments but 2 were given"** 时，八成就是漏了 `self` —— 那个"多出来"的参数就是 Python 自动传进去的实例。

### 覆盖父类方法：签名只能「放宽」，不能「收紧」

- **一句话结论**：子类改写父类方法时，要能接住**父类能接受的所有调用** —— 可以多收参数、可以给默认值，但**不能把可选参数改成必填**。
- **为什么**：框架（以及任何用到父类的地方）是照着**父类的签名**写的，它不知道你的子类长什么样。你把可选参数变必填，那些调用就会崩。这叫**里氏替换原则**：子类对象必须能替代父类对象。
- **示例**：

  ```python
  class Parent:
      def f(self, tools, *, mode=None, **kwargs):
          ...

  class Bad(Parent):
      def f(self, tools, mode):                  # ❌ mode 变成必填，破坏契约
          ...

  class Good(Parent):
      def f(self, tools, mode=None, **kwargs):   # ✅ 兼容
          ...
  ```

- **踩坑点**：**"我的代码能跑通"不代表签名是对的** —— 可能只是恰好没有调用者走到那条更宽松的路径。

### `**kwargs`：接住「所有没点名的关键字参数」

- **一句话结论**：`def f(self, tools, **kwargs)` 里的 `**kwargs` 会把调用时**多出来的关键字参数**打包成一个字典收下，函数就不会因为"不认识这个参数"而报错。
- **为什么**：框架调用你的方法时会附带一些你自己的代码用不到的参数（比如 `tool_choice`）。写上 `**kwargs` 就是"这些都收下、我不处理"，比一个个列出来稳妥。
- **示例**：

  ```python
  def f(a, **kwargs):
      print("a =", a)
      print("其余 =", kwargs)

  f(1, b=2, c=3)   # a = 1 ; 其余 = {'b': 2, 'c': 3}
  f(1)             # a = 1 ; 其余 = {}
  ```

- **踩坑点**：`*args` 收**位置**参数（打包成元组），`**kwargs` 收**关键字**参数（打包成字典）。看到 `unexpected keyword argument 'xxx'` 时，要么显式写进签名，要么加 `**kwargs`。

---

## 类型与自省

### 判断类型用 `isinstance()`，不要用 `type(x) ==`

- **一句话结论**：判断"是不是某种类型"用 `isinstance(x, 类)`；`type(x) == 类` 只认**完全相同**的类型，子类实例会被判为 `False`。
- **为什么**：`isinstance` 会考虑继承关系，这也是 Python 的惯例写法。
- **示例**：

  ```python
  class Animal: pass
  class Dog(Animal): pass

  d = Dog()
  print(type(d) == Animal)        # False —— 子类不算
  print(isinstance(d, Animal))    # True  —— 正确
  ```

- **踩坑点**：如果对象**自带**一个表示种类的字段（比如 LangChain 消息的 `.type`），那比判断类型更好。

### `type()` 是内置函数，不是对象的方法

- **一句话结论**：查类型写 `type(x)`，**不是** `x.type()`。
- **为什么**：`type` 是 Python 内置的**函数**，作用于任何对象；它不是对象身上的方法。有些库的对象确实自带 `.type` 属性（比如 LangChain 的消息），所以很容易混淆 —— 但那是「数据字段」，不是「查类型」。
- **示例**：

  ```python
  print(type("hi"))     # <class 'str'>
  print(type(print))    # <class 'builtin_function_or_method'>
  "hi".type()           # AttributeError: 'str' object has no attribute 'type'
  ```

- **踩坑点**：分清这两类 —— 名字带 `__` 的（`__doc__`、`__name__`）是**属性**，用时不加括号；`type` / `len` / `print` 是**函数**，要加括号。

### 自省三件套：`type()` / `dir()` / `vars()`

- **一句话结论**：想知道一个对象有什么，别猜也别背 —— `type(x)` 看它是什么，`vars(x)` 看它自己存了什么数据，`dir(x)` 看它总共能访问到哪些名字。
- **为什么**：Python 的属性和方法都摆在对象上，可以随时问它。这是读陌生库代码时最省时间的手段。
- **示例**：

  ```python
  class Dog:
      def __init__(self, name):
          self.name = name
      def bark(self):
          return "woof"

  d = Dog("旺财")
  print(type(d))      # <class '__main__.Dog'>
  print(vars(d))      # {'name': '旺财'}
  print([a for a in dir(d) if not a.startswith("_")])   # ['bark', 'name']
  ```

- **踩坑点**：`vars()` 只列**这个实例自己存**的数据，**会漏掉类上定义的属性和方法**。实用顺序：先 `vars()` 快速扫，缺什么再用 `dir()` 兜底。
- **另外两个省事办法**：IDE 里敲 `obj.` 按补全键；以及 `help(obj)` 打印类和方法的说明。

### 属性不等于数据：`property` 是按需算出来的

- **一句话结论**：`x.foo` 不一定存在对象里，它可能是**类上定义的 property**，每次访问时现算出来。
- **为什么**：Python 查找属性时先找实例自己的数据，再找类上的描述符。property 就是描述符的一种，所以它**不会**出现在 `vars(x)` 里。
- **示例**：

  ```python
  class Circle:
      def __init__(self, r):
          self.r = r

      @property
      def area(self):
          return 3.14159 * self.r ** 2

  c = Circle(2)
  print(vars(c))    # {'r': 2}     —— 没有 area
  print(c.area)     # 12.566...    —— 但能访问，因为是现算的
  ```

- **踩坑点**：`vars()` 里找不到 **≠** 不能访问；能访问 **≠** 数据真的存在对象里。

### 单元素括号不是元组：`("hi")` 就是 `"hi"`

- **一句话结论**：圆括号只负责**分组**，不负责造元组。造元组的是**逗号**。
- **为什么**：`("hi")` 里没有逗号，Python 认为它只是被括号包起来的字符串。
- **示例**：

  ```python
  a = ("hi")
  b = ("hi",)
  print(type(a))   # <class 'str'>
  print(type(b))   # <class 'tuple'>
  print(len(b))    # 1
  ```

- **踩坑点**：想传"一个元素的元组"必须写 `("hi",)`。反过来，`("hi")` 能当字符串用，所以写错了往往**不报错**，只是行为和你以为的不一样 —— 这类错误最难发现。

### 类型注解的另一面：`@tool` 会用它校验并转换参数

- **一句话结论**：普通 Python 函数的注解**不校验**，但 `@tool` 装饰后，框架会根据注解建一个校验结构，把能转的类型**转过去**（`"1"` → `1`）。
- **为什么**：`@tool` 从你的函数签名生成参数 schema，运行时先按 schema 校验 / 转换，再调用你的函数。
- **示例**：

  ```python
  def add(a: int, b: int) -> int:
      return a + b

  print(add("1", "2"))                           # 12 —— 普通函数不校验，字符串拼接

  @tool
  def add_tool(a: int, b: int) -> int:
      """两数相加。"""
      return a + b

  print(add_tool.invoke({"a": "1", "b": "2"}))   # 3 —— 被转换成了整数
  ```

- **踩坑点**：这两件事不矛盾 —— **普通函数的注解是"说明"，工具对象的注解是"契约"**。
- **验证时的坑**：想验证"注解不校验"，必须确认你**真的传了字符串**（传 `1` 和传 `"1"` 是两个不同的实验），而且用的是**没被装饰的普通函数**。拿错一个，结论就反了。

### Python 没有 `virtual`：所有方法默认可覆盖，契约由「调用方」强制

- **一句话结论**：Python **没有 `virtual` 关键字**，因为所有方法默认就是"虚的" —— 子类定义同名方法就自动生效，不需要任何声明。而"你必须实现某个方法、参数必须一致"这件事，**不由语言强制，由调用方在运行时强制**。
- **为什么**：`obj.method()` 的查找是**动态**的 —— 先找实例所属的类，找不到才沿继承链往上。所以覆盖是默认行为，不是特权。
- **两种"要求你实现"的写法，代价完全不同**：

  | 写法 | 你不实现会怎样 |
  | --- | --- |
  | `@abstractmethod` | **实例化时**就报错 —— 对象根本建不出来 |
  | 方法体里 `raise NotImplementedError` | **调用时**才报错 —— 对象能建、能用，直到有人真的用到它 |

- **示例**：

  ```python
  class Base:
      def greet(self):
          """打个招呼。"""
          raise NotImplementedError   # 空壳：有签名、有文档，一调用就炸

  class Child(Base):
      pass                            # 不覆盖也能实例化！

  Child().greet()     # 对象建得出来；调用时才报 NotImplementedError
  ```

- **踩坑点**：
  - **签名不匹配不会在"定义时"报错**，只在"调用时"崩。所以**"我的代码能跑通"不代表签名是对的** —— 可能只是恰好没走到那条路径。
  - 框架调你的方法是**照着父类签名调的**，这就是为什么覆盖时签名只能放宽、不能收紧。
  - 这个模式叫**控制反转（IoC）**：你提供零件，框架在正确的时机调用你。**是你去实现接口，不是你去调框架** —— 你写的 `bind_tools` 是**回调**，不是自己手动调的函数。

### Pydantic 模型里不要用下划线类属性做开关

- 一句话结论：在 Pydantic 模型的类体里写 `_flag = False`，判断 `if not _flag` **恒为假**，那段代码永远不执行。
- 为什么：Pydantic 把下划线开头的类属性识别为「私有属性」，包成一个描述符对象。描述符对象本身是真值，
  所以 `not _flag` 恒为 `False` —— 不是语法错，是**静默失效**。
- 示例：

  ```python
  class M(BaseModel):
      _printed = False          # ❌ 被 Pydantic 接管，判断恒为假

  _PRINTED = False              # ✅ 模块级变量，Pydantic 管不着

  class M2(BaseModel):
      def run(self):
          global _PRINTED
          if not _PRINTED:
              _PRINTED = True
              print("正常执行")
  ```

- 踩坑点：不报错、不执行 —— 最难查的一类。替代方案：实例字段、`PrivateAttr()`、模块级变量。
