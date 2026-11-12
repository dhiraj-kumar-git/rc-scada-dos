## Constraints for the DFX smoke test (top_dfx): clock, LEDs, and the
## reconfigurable region (Pblock) for u_rm.
set_property PACKAGE_PIN Y9 [get_ports clk]
set_property IOSTANDARD LVCMOS33 [get_ports clk]
create_clock -period 10.000 -name sys_clk [get_ports clk]

set_property PACKAGE_PIN T22 [get_ports {led[0]}]
set_property PACKAGE_PIN T21 [get_ports {led[1]}]
set_property PACKAGE_PIN U22 [get_ports {led[2]}]
set_property PACKAGE_PIN U21 [get_ports {led[3]}]
set_property PACKAGE_PIN V22 [get_ports {led[4]}]
set_property PACKAGE_PIN W22 [get_ports {led[5]}]
set_property PACKAGE_PIN U19 [get_ports {led[6]}]
set_property PACKAGE_PIN U14 [get_ports {led[7]}]
set_property IOSTANDARD LVCMOS33 [get_ports {led[*]}]

## Reconfigurable region: one clock region high (rows 100 to 149, clock region X0Y2), 20 slice columns.
## On the XC7Z020 the processing system occupies slice columns 0 to 25 in rows 50 to 149, so the range starts at column 26.
create_pblock pblock_rm
add_cells_to_pblock [get_pblocks pblock_rm] [get_cells u_rm]
resize_pblock [get_pblocks pblock_rm] -add {SLICE_X26Y100:SLICE_X45Y149}
## The same rectangle also holds one DSP and one block RAM column: range them too (DRC HDPR-45)
resize_pblock [get_pblocks pblock_rm] -add {DSP48_X2Y40:DSP48_X2Y59 RAMB18_X2Y40:RAMB18_X2Y59 RAMB36_X2Y20:RAMB36_X2Y29}
set_property SNAPPING_MODE ON [get_pblocks pblock_rm]
