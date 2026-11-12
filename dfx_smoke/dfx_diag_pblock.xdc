## Reconfigurable partition u_rm for the E2 modules (rm_detector, rm_net_diag,
## rm_modbus_diag): the whole clock region X1Y2, one clock region high, right
## of the processing system. A full clock region includes every site type
## (slices, block RAM, DSP), so the largest module (rm_net_diag: sketch D = 4)
## fits and DRC HDPR-45 has nothing to report.
create_pblock pblock_rm
add_cells_to_pblock [get_pblocks pblock_rm] [get_cells u_rm]
## Written as explicit site ranges (all of clock region X1Y2, listed with Vivado):
## 2600 slices, 30 RAMB36, 60 RAMB18, 40 DSP48.
resize_pblock [get_pblocks pblock_rm] -add {SLICE_X50Y100:SLICE_X113Y149}
resize_pblock [get_pblocks pblock_rm] -add {RAMB18_X3Y40:RAMB18_X5Y59 RAMB36_X3Y20:RAMB36_X5Y29}
resize_pblock [get_pblocks pblock_rm] -add {DSP48_X3Y40:DSP48_X4Y59}
set_property SNAPPING_MODE ON [get_pblocks pblock_rm]
