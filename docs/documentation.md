# DigSim Documentation

* **Table of contents**
  * **[GUI Application](#gui-application)**
    * [Components](#components)
    * [Wires](#wires)
  * **[Python Circuits](#python-circuits)**

# GUI Application

## Components

### Input Components

 * Push Button - A Push Button will change its output when it is pressed
   <br/><img alt="Button" src="../src/digsim/app/gui_objects/images/PB.png"/> 
 * On/Off Switch - An on/off switch will change its output when it is toggled
   <br/><img alt="Switch" src="../src/digsim/app/gui_objects/images/Switch_ON.png"/>
 * Clock - A clock will change its output with a certain frequency
   <br/><img alt="Clock" src="../src/digsim/app/gui_objects/images/Clock.png"/>
 * Static Value - A static value can be setup to output value on a wire or a bus.
   <br/><img alt="Static Value" src="../src/digsim/app/gui_objects/images/ZERO.png"/>

### Output Components

* LED - A LED output will be lit if it is driver by a logic one / high signal.
* Hex Digit - A Hex Digit will show the value on a bus (4 / 8 / 12 / 16 bits)
* 7-Segment Display - A 7-Segment is almost the same as a hex digit but each segment can be controlled individually. 

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

Wires are used to connect component ports. A source port can drive multiple sink ports. The source and sink port must be of the same type, i.e. a wire or a bus with the same bus width. If a a bus needs to be splitted the [Bus/Wire Converters](#buswire-converters) can be used.    



# Python Circuits

