# Create a hardware platform (XSA) with only the Zynq processing system, using
# the ZedBoard preset (DDR3, UART1, clocks), for the bare-metal ARM programs
# c/zynq_main.c and c/sketch_zynq_main.c. No bitstream is needed.
# Needs the Digilent board files (https://github.com/Digilent/vivado-boards).
# Run from the repo root, passing the board_files folder:
#   vivado -mode batch -nolog -source scripts/build_arm_platform.tcl -tclargs <path>/vivado-boards-master/new/board_files
# Output: build/arm_platform.xsa

set root [file normalize [file join [file dirname [info script]] ..]]
if {$argc < 1} { error "pass the Digilent board_files folder as the first -tclargs argument" }
set_param board.repoPaths [list [file normalize [lindex $argv 0]]]
set proj_dir [file normalize [file join $root .. vivado_arm_platform]]
file mkdir [file join $root build]

create_project arm_platform $proj_dir -part xc7z020clg484-1 -force
set bp [lindex [lsort [get_board_parts -quiet digilentinc.com:zedboard:part0:*]] end]
if {$bp eq ""} { error "ZedBoard board part not found: check the board_files folder" }
set_property board_part $bp [current_project]

create_bd_design ps_only
set ps [create_bd_cell -type ip -vlnv xilinx.com:ip:processing_system7 ps7]
apply_bd_automation -rule xilinx.com:bd_rule:processing_system7 \
    -config {make_external "FIXED_IO, DDR" apply_board_preset "1" Master "Disable" Slave "Disable"} $ps
# No PL connection is needed: turn off the general-purpose AXI master so it needs no clock
set_property CONFIG.PCW_USE_M_AXI_GP0 0 $ps
validate_bd_design
save_bd_design

set bd [get_files ps_only.bd]
generate_target all $bd
add_files -norecurse [make_wrapper -files $bd -top]
set_property top ps_only_wrapper [current_fileset]
update_compile_order -fileset sources_1

write_hw_platform -fixed -force -file [file join $root build arm_platform.xsa]
puts "ARM_PLATFORM_RESULT xsa=build/arm_platform.xsa board=$bp ddr=[get_property CONFIG.PCW_UIPARAM_DDR_PARTNO $ps] cpu_mhz=[get_property CONFIG.PCW_APU_PERIPHERAL_FREQMHZ $ps] uart1=[get_property CONFIG.PCW_UART1_PERIPHERAL_ENABLE $ps]"
