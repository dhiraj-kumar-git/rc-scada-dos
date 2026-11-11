## Milestone 1 constraints for replay_top on the ZedBoard.
## Pins follow the Digilent ZedBoard master XDC. Check them once against the
## master XDC from Digilent before the first build.

## 100 MHz clock (GCLK)
set_property PACKAGE_PIN Y9 [get_ports clk]
create_clock -period 10.000 -name sys_clk [get_ports clk]

## Centre push button
set_property PACKAGE_PIN P16 [get_ports btnc]

## Slide switches SW0, SW1 (region select)
set_property PACKAGE_PIN F22 [get_ports {sw[0]}]
set_property PACKAGE_PIN G22 [get_ports {sw[1]}]

## User LEDs LD0..LD7
set_property PACKAGE_PIN T22 [get_ports {led[0]}]
set_property PACKAGE_PIN T21 [get_ports {led[1]}]
set_property PACKAGE_PIN U22 [get_ports {led[2]}]
set_property PACKAGE_PIN U21 [get_ports {led[3]}]
set_property PACKAGE_PIN V22 [get_ports {led[4]}]
set_property PACKAGE_PIN W22 [get_ports {led[5]}]
set_property PACKAGE_PIN U19 [get_ports {led[6]}]
set_property PACKAGE_PIN U14 [get_ports {led[7]}]

## I/O standards by bank, as in the Digilent master XDC.
## Banks 13 and 33 are fixed at 3.3 V on the ZedBoard.
set_property IOSTANDARD LVCMOS33 [get_ports -of_objects [get_iobanks 13]]
set_property IOSTANDARD LVCMOS33 [get_ports -of_objects [get_iobanks 33]]
## Banks 34 and 35 follow the VADJ jumper (J18). The master XDC default is 1.8 V.
## If your J18 is set to 2.5 V, change these two lines to LVCMOS25.
set_property IOSTANDARD LVCMOS18 [get_ports -of_objects [get_iobanks 34]]
set_property IOSTANDARD LVCMOS18 [get_ports -of_objects [get_iobanks 35]]
