# DigSim Documentation

* **Table of contents**
  * **[GUI Application](#gui-application)**
    * [Components](#components)
    * [Wires](#wires)
  * **[Python Circuits](#python-circuits)**

# GUI Application

## Components

### Input Components

#### Push Button

#### On/Off Switch

#### Clock

#### Static Value

### Output Components

#### LED

#### Hex Digit

#### 7-Segment Display

### Logic Gates

The basic logic gates have been implemented
  * OR
  * AND
  * NOT
  * XOR
  * NOR
  * NAND
 
### Flip Flops
  * D Flip Flop
  * SR Flip Flop
  * JK Flip Flop
  * T Flip FLop

### Multiplexer

### Bus/Wire Converters

### IC Components

### Yosys Component

### Notes

## Wires

Wires are used to connect component ports. A source port can drive multiple sink ports. The source and sink port must be of the same type, i.e. a wire or a bus with the same bus width. If a a bus needs to be splitted the [Bus/Wire Converters](#bus-wire-converters) can be used.    



# Python Circuits

