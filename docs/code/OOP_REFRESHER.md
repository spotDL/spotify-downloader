<!--- mdformat-toc start --slug=github --->

<!-- refresher on Object Oriented Programing -->

# Object Oriented Programing (*noun.*)

It's a set of principles to handle complexity invented at Xerox Parc alongside the GUI.
Theses principles are more important the bigger the codebase.

We don't go into icky terminology here, just a couple of analogies.

______________________________________________________________________

# Index

1. [Abstraction](#Abstraction)
2. [Encapsulation](#Encapsulation)
3. [Polymorphism](#Polymorphism)
4. [Inheritance](#Inheritance)
5. [A Gist](#Gist) (for lazy guys & gals)

______________________________________________________________________

# The principles

## Abstraction

Abstraction is basically simplification - a car is not 100 screws of x size, 10032 screws
of y size, 15 metal panels of this shape, 30 plastic panels of that shape, a steering
wheel with a drive rod, wiring and a horn and a few thousand other parts working in unison
perfectly resulting in 4 tires moving so that the whole vehicle moves forwards. A car is
a chassis, an engine, a steering system, seats and safety features working to move a
vehicle.

The second, systems based explanation is easier to comprehend and manage. In other terms,
abstraction is the ***breaking down of a big complex system
into smaller, self-contained and single-purpose sub-systems*** and if necessary, even
sub-sub-sub-systems. The key requirements here would be 'small', 'single-purpose' and
'self-contained' subsystems.

```python
# An example of bad Abstraction.

# a class named masterClass should ring alarm bells
billingCounter = masterClass()

# products still in the store and how many units are left
inventory = billingCounter.getInventory()
print(inventory)        # {'akja fruit': 15,
                        # 'sambesa': 93,
                        # ...,
                        # 'zabberwokey fry': 19
                        # }

# 198 customers had their products billed at this counter
totalSales = billingCounter.getNumberOfSales()
print(totalSales)       # 198

# 19,763u worth profits were made (u --> units, star wars currency)
totalProfits = getProfit('today', billingCounter)
print(totalProfits)     # 19,763
```

Why is the above a bad example of Abstraction? It's not single purpose or self-contained.
It's not single purpose because inventory has absolutely no relation with number of sales.
It is not self contained because lets assume that `masterClass` majorly deals with
finances - number of sales, profits, etc... having a function `getProfit` outside or the
class breaks its 'self-contained-ness'. Some might argue otherwise but then, OOP is a set
of principles, they are still a tiny bit subjective in nature.

```python
# This is a properly abstracted version of the previous 'bad' example. I do
# realize that this is an absurd example but it serves its purpose so...
#
# The outputs are the same as before

# inventory handling
inventory = inventoryClass()

currentInventory = inventory.getInventory()
print(currentInventory)

# finance handling
finances = financeClass()

totalSales = finances.getNumberOfSales()
print(totalSales)

totalProfits = finances.getProfits('today')
print(totalProfits)
```

Yep, this is a bit longer, there is an additional class and the class names are absurd,
but the above version of the 'bad' example is more descriptive through the code itself and
also no one is scratching their heads as to what else the `billingCounter` object can dish
out beyond inventory and finances. The perks of proper abstraction might not be visible
in this rather silly example, but be rest assured, the bigger your codebase gets the more
dangerous lack of abstraction becomes.

______________________________________________________________________

## Encapsulation

While abstraction is all about simplification, encapsulation is about consistent
abstraction. In essence, encapsulation says that if 'chassis' is a referred to as a
sub-component of a car, you can't go down to the details and start talking about some nut
and bolt fitted on the door hinge. Encapsulation is about
***ensuring a constant level of abstraction***. Not so clear huh? Nothing like a straight
forward coded example.

```python
# An example of bad encapsulation

# lets say that the inventory class provides access to the inventories of all
# star wars superMarkets across the galaxy.
inventory = inventoryClass()

# d4a7 is the code of a superMarket on Tatooine, a star wars desert planet
productCategory = inventory.getInventory('d4a7')['akja fruit'].details.category
print('category of akja fruit is ' + productCategory)
                                            # category of akja fruit is 'fruit'
```

Why is this bad encapsulation? Because it breaks from a consistent level of abstraction.
The `inventoryClass` is meant to simplify complexity, it deals at the level of
inventories/products. to pull something like
`getInventory('d4a7')['akja fruit'].details.category` means talking about details from a
lower level of abstraction. The problem arises when someone tries to read your code, that
person now has to know the inner workings of how products are stored in the
`inventoryClass` to understand the above code which make to whole point of abstraction
wasteful.

```python
# A better version of the 'bad' example.
#
# Outputs are same as before

inventory = inventoryClass()

tatooineInventory = inventory.getInventory('d4a7')
productCategory = tatooineInventory.getCategory('akja fruit')
print('category of akja fruit is ' + productCategory)
```

There is a lot of freedom to be gained by directly referencing details from lower levels
of abstraction but for any project over 500 lines, the freedom is not worth the confusion
and chaos it will eventually cause. The same extent of functionality can be produced with
encapsulation like the example utilized a `getCategory` function, but adding function upon
function to provide the same freedom/flexibility while ensuring encapsulation goes
against the basic purpose of managing complexity (who can keep track of 20 functions
provided by a single class?). Eventually you have to tradeoff 'managing of complexity'
against 'freedom/flexibility'. In 99% or cases with codebases above 500 lines, it'd be
better to manage complexity first and bother about flexibility/freedom later.

Some coders enforce consistent abstraction via 'data hiding'. This author personally
encourages such practices.

______________________________________________________________________

## Polymorphism

Polymorphism comes from the greek words meaning 'different shapes', Polymorphism is a
'generalization' relation - the ability to handle different classes/objects the same way
(OR) the capability to use an instance without regard for its type. One of the most common
ways of implementing polymorphism is via interfaces.

```python
# A bad example of polymorphism
#
# Print the areas of different shapes

circle = shapeCircle(radius = 7)
area = circle.area()
print(area)

squire = shapeSquire(side = 5)
area = squire.sideSquire()
print(area)

rhombus = shapeRhombus(diagonals = (1, 5))
area = rhombus.calculateArea()
print(area)

triangle = shapeTriangle(a = 15, b = 10, c = 13)
area = triangle.halfBaseTimesHeight()
print(area)

# Remake of the 'bad' example using polymorphism

circle = shapeCircle(radius = 7)
squire = shapeSquire(side = 5)
rhombus = shapeRhombus(diagonals = (1,5))
triangle = shapeTriangle(a = 15, b = 10, c = 13)

shapes = [circle, squire, rhombus, triangle]

for shape in shapes:
    area = shape.getArea()
    print(area)
```

What's the difference? In the polymorphism based remake, the method to get area is
standardized, this means that different shape classes that require deferent calculation to
obtain the area can now be treated the exact same way.

______________________________________________________________________

## Inheritance

Inheritance works alongside polymorphism just as abstraction works with encapsulation.
while polymorphism is a 'generalization' relation. Inheritance is a 'specialization'
relation. Don't build everything from scratch - leave the common features be, it reduces
the details you have to keep in mind while coding.

```python
# An example without inheritance

class car(object):
    # code goes here

    def getNumberPlate(self):
        return self.registrationNumber
    
    def getVehicleName(self):
        return self.model
    
    # more code

class bike(object):
    # code goes here

    def getNumberPlate(self):
        return self.numberPlate
    
    def getVehicleName(self):
        return self.bikeName
    
    # more code

class tractor(object):
    # code goes here

    def getNumberPlate(self):
        return self.companyProvidedNumber
    
    def getVehicleName(self):
        return self.modelName
    
    # more code
```

The polymorphism followed here make these objects fairly manageable but for someone
reading all of this code, he/she/them will have to read through the same set of code
multiple times. This usually causes two problems - ballooning of code and confusion that
arises from reading the same set of code again and again in the context of different
variables - *was it `self.modelName`
or `self.bikeName` or `self.model`? I'm confused...*

```python
# An inheritance based example

class vehicle(object):
    # code goes here

    def getNumberPlate(self):
        return self.numberPlate
    
    def getVehicleName(self):
        return self.name
    
    # more code

class car(vehicle):
    # car specific functions

class bike(vehicle):
    # bike specific functions

class tractor(vehicle):
    # tractor specific functions

```

This example treat's `car`, `bike`, and `tractor` as special instances of `vehicle`,
removing a lot of the confusion that accompanies the earlier example. Know what a
particular function does in a parent class to a large extent allows you to know what a
'child class' does. Only one note of warning here, use shallow inheritance, deep
inheritance trees will have you searching for which parent/super-parent defines a
particular variable/function and which parent/super-parent modifies those same
variables/functions leading to a confusing mess.

______________________________________________________________________

# Gist

1. Abstraction

   - breaking down of a big complex system into smaller, self-contained and single-purpose
     sub-systems
   - emphasis on ***small, self-contained*** and ***single-purpose***
   - extra emphasis on ***self-contained*** and ***single-purpose***
   - extra extra extra emphasis on ***single-purpose***
   - Now read that ***x3 times*** over

2. Encapsulation

   - consistent level of abstraction (emphasis on ***consistent***)
   - A.K.A, no public referencing of internal-attributes, ***especially*** if the attributes
     are ***complex objects***
   - `knifeCompany = house.kitchen.knife.company.name`, ***DON'T DO THIS!***
   - ***hide as much as possible*** - enforce encapsulation

3. Polymorphism

   - generalization relation - the capability to use an instance without regard for its type
   - use ***standard interfaces*** for members of a logical class (triangles and circles belong
     to the same logical class - 'shapes') as far as possible

4. Inheritance

   - specialization relation - don't build everything from scratch
   - ***beware of deep inheritance*** - i.e. more than 5 levels of inheritance
