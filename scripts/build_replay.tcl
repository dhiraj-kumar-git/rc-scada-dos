# Create the Vivado project for replay_top and build the bitstream.
# UNTESTED until it runs on the team's Vivado. Run from the repo root on Windows:
#   vivado -mode batch -source scripts/build_replay.tcl
# From WSL (adjust the Vivado version folder):
#   cmd.exe /c "cd /d C:\rc\rc-scada-dos && C:\Xilinx\Vivado\<version>\bin\vivado.bat -mode batch -source scripts\build_replay.tcl"
# Outputs: build/replay_top.bit, build/vivado_utilization.txt, build/vivado_timing.txt
# The repo path must not contain spaces.

set root [file normalize [file join [file dirname [info script]] ..]]
set proj_dir [file normalize [file join $root .. vivado_replay]]
file mkdir [file join $root build]

foreach f {rtl/rules.vh rtl/regions.vh rtl/records.mem} {
    if {![file exists [file join $root $f]]} {
        error "$f is missing: run make rules and make demo first (or copy from selftest/rtl for a toolchain-only build)"
    }
}

create_project replay $proj_dir -part xc7z020clg484-1 -force
add_files [list \
    [file join $root rtl detector.v] \
    [file join $root rtl replay_top.v] \
    [file join $root rtl rules.vh] \
    [file join $root rtl regions.vh] \
    [file join $root rtl records.mem]]
set_property file_type {Verilog Header} [get_files rules.vh]
set_property file_type {Verilog Header} [get_files regions.vh]
set_property include_dirs [list [file join $root rtl]] [current_fileset]
set_property top replay_top [current_fileset]
# absolute path for $readmemh, so synthesis always finds the records
set memfile [file join $root rtl records.mem]
set_property generic "MEMFILE=\"$memfile\"" [current_fileset]
add_files -fileset constrs_1 [file join $root constraints zedboard_replay.xdc]

launch_runs synth_1 -jobs 4
wait_on_run synth_1
if {[get_property PROGRESS [get_runs synth_1]] != "100%"} { error "synthesis failed: see $proj_dir/replay.runs/synth_1/runme.log" }

launch_runs impl_1 -to_step write_bitstream -jobs 4
wait_on_run impl_1
if {[get_property PROGRESS [get_runs impl_1]] != "100%"} { error "implementation failed: see $proj_dir/replay.runs/impl_1/runme.log" }

open_run impl_1
report_utilization -file [file join $root build vivado_utilization.txt]
report_timing_summary -file [file join $root build vivado_timing.txt]
set wns [get_property SLACK [get_timing_paths -max_paths 1 -nworst 1 -setup]]
set bram [llength [get_cells -hierarchical -filter {REF_NAME =~ RAMB*}]]
file copy -force [file join $proj_dir replay.runs impl_1 replay_top.bit] [file join $root build replay_top.bit]
puts "BUILD_RESULT wns_ns=$wns block_ram_cells=$bram bitstream=build/replay_top.bit"
if {$wns < 0} { puts "BUILD_RESULT FAIL: timing not met" } else { puts "BUILD_RESULT PASS: timing met" }
if {$bram == 0} { puts "BUILD_RESULT FAIL: no block RAM, records.mem was not used" }
