# Program the ZedBoard (PROG/JTAG USB port connected, board powered on).
# UNTESTED until it runs on the team's Vivado. Run from the repo root:
#   vivado -mode batch -source scripts/program_m1.tcl
# Optional argument: a different .bit file
#   vivado -mode batch -source scripts/program_m1.tcl -tclargs build/top_dfx.bit
set root [file normalize [file join [file dirname [info script]] ..]]
set bit [file join $root build replay_top.bit]
if {$argc > 0} { set bit [file normalize [lindex $argv 0]] }
if {![file exists $bit]} { error "bitstream not found: $bit" }
open_hw_manager
connect_hw_server
open_hw_target
set dev [lindex [get_hw_devices xc7z020*] 0]
if {$dev eq ""} { error "no xc7z020 device found: check the USB cable and board power" }
current_hw_device $dev
set_property PROGRAM.FILE $bit $dev
program_hw_devices $dev
puts "M1_RESULT programmed $bit"
close_hw_manager
