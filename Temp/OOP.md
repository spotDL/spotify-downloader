# What is Object Oriented Programing?

It's a set of principles to handle complexity. Object Oriented Programing was
invented at Xerox Parc alongside the GUI. Theses principles are more important
the bigger the codebase.

We don't go into icky terminology here, just a couple of analogies.

# The principles

## Abstraction

Abstraction is basically simplification - a car is not 100 screws of x size,
10032 screws of y size, 15 metal panels of this shape, 30 plastic panels of
that shape, a steering wheel with a drive rod, wiring and a horn and a few
thousand other parts working in unison perfectly resulting in 4 tires moving
so that the whole vehicle moves forwards. A car is a chassis, an engine, a
steering system, seats and safety features working to move a vehicle.

The second, systems based explanation is easier to comprehend and manage.
In other terms, abstraction is the ***breaking down of a big complex system
into smaller, self-contained and single-purpose sub-systems*** and if
necessary, even sub-sub-sub-systems. The key requirements here would be
'small', 'single-purpose' and 'self-contained' subsystems.

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

Why is the above a bad example of Abstraction? It's not single purpose or
self-contained. It's not single purpose because inventory has absolutely no
relation with  number of sales. It is not self contained because lets assume
that `masterClass` majorly deals with finances - number of sales, profits,
etc... having a function `getProfit` outside or the class breaks its
'self-contained-ness'. Some might argue otherwise but then, OOP is a set of
principles, they are still a tiny bit subjective in nature.

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

Yep, this is a bit longer, there is an additional class and the class names are
absurd, but the above version of the 'bad' example is more descriptive through
the code itself and also no one is scratching their heads as to what else the
`billingCounter` object can dish out beyond inventory and finances. The perks
of proper abstraction might not be visible in this rather silly example, but be
rest assured, the bigger your codebase gets the more dangerous lack of
abstraction becomes.

<br><br>

## Encapsulation

While abstraction is all about simplification, encapsulation is about
consistent abstraction. In essence, encapsulation says that if 'chassis' is
a referred to as a sub-component of a car, you can't go down to the details
and start talking about some nut and bolt fitted on the door hinge.
Encapsulation is about ***ensuring a constant level of abstraction***.
Not so clear huh? Nothing like a straight forward coded example.

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

Why is this bad encapsulation? Because it breaks from a consistent level of
abstraction. The `inventoryClass` is meant to simplify complexity, it deals
at the level of inventories/products. to pull something like
`getInventory('d4a7')['akja fruit'].details.category` means talking about
details from a lower level of abstraction. The problem arises when someone
tries to read your code, that person now has to know the inner workings of
how products are stored in the `inventoryClass` to understand the above code
which make to whole point of abstraction wasteful.

```python
# A better version of the 'bad' example.
#
# Outputs are same as before

inventory = inventoryClass()

tatooineInventory = inventory.getInventory('d4a7')
productCategory = tatooineInventory.getCategory('akja fruit')
print('category of akja fruit is ' + productCategory)
```

There is a lot of freedom to be gained by directly referencing details from
lower levels of abstraction but for any project over 500 lines, the freedom is
not worth the confusion and chaos it will eventually cause. The same extent of
functionality can be produced with encapsulation like the example utilized a
`getCategory` function, but adding function upon function to provide the same
freedom/flexibility while ensuring encapsulation goes against the basic purpose
of managing complexity (who can keep track of 20 functions provided by a single
class?). Eventually you have to tradeoff 'managing of complexity' against
'freedom/flexibility'. In 99% or cases with codebases above 500 lines, it'd be
better to manage complexity first and bother about flexibility/freedom later.

<br><br>

## Polymorphism / Inheritance

*Not completely sure of this part, will update after a wikipedia lookup.*

<br><br>

## Go [back](../README.md#The%20requirements) to where you left off