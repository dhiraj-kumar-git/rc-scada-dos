# DFX smoke test, non-project flow (UG909): one static design, one
# reconfigurable partition (u_rm), two reconfigurable modules.
# UNTESTED until it runs on the team's Vivado. No board needed.
# Run from the repo root:
#   vivado -mode batch -source scripts/dfx_smoke.tcl
# Outputs in build/dfx/:
#   config_count.bit                    full bitstream, counter module loaded
#   config_count_pblock_rm_partial.bit  partial bitstream: counter module
#   config_walk.bit                     full bitstream, walking-LED module loaded
#   config_walk_pblock_rm_partial.bit   partial bitstream: walking-LED module
# (exact partial file names are printed by write_bitstream; check the log)

set root [file normalize [file join [file dirname [info script]] ..]]
set out  [file join $root build dfx]
set part xc7z020clg484-1
file mkdir $out

# 1. Static design, with rm_pattern as a black box
read_verilog [file join $root dfx_smoke top_dfx.v]
read_verilog [file join $root dfx_smoke rm_pattern_bb.v]
synth_design -top top_dfx -part $part
write_checkpoint -force [file join $out static_synth.dcp]
close_project

# 2. Each reconfigurable module, synthesised out of context
foreach rm {rm_count rm_walk} {
    read_verilog [file join $root dfx_smoke $rm.v]
    synth_design -mode out_of_context -top rm_pattern -part $part
    write_checkpoint -force [file join $out ${rm}_synth.dcp]
    close_project
}

# 3. Configuration 1: static + counter module
open_checkpoint [file join $out static_synth.dcp]
read_checkpoint -cell u_rm [file join $out rm_count_synth.dcp]
set_property HD.RECONFIGURABLE true [get_cells u_rm]
read_xdc [file join $root dfx_smoke dfx_smoke.xdc]
opt_design
place_design
route_design
report_utilization -file [file join $out config_count_utilization.txt]
report_timing_summary -file [file join $out config_count_timing.txt]
write_checkpoint -force [file join $out config_count_routed.dcp]
write_bitstream -force [file join $out config_count]
# keep the static routing, empty the partition
update_design -cell u_rm -black_box
lock_design -level routing
write_checkpoint -force [file join $out static_routed.dcp]
close_project

# 4. Configuration 2: the same locked static + walking-LED module
open_checkpoint [file join $out static_routed.dcp]
read_checkpoint -cell u_rm [file join $out rm_walk_synth.dcp]
opt_design
place_design
route_design
report_timing_summary -file [file join $out config_walk_timing.txt]
write_checkpoint -force [file join $out config_walk_routed.dcp]
write_bitstream -force [file join $out config_walk]
close_project

# 5. Check that both configurations share an identical static design
pr_verify -initial [file join $out config_count_routed.dcp] -additional [file join $out config_walk_routed.dcp] -file [file join $out pr_verify.txt]
puts "DFX_RESULT done: bitstreams in build/dfx, pr_verify report in build/dfx/pr_verify.txt"
foreach f [glob -nocomplain -directory $out *.bit] { puts "DFX_RESULT bitstream [file tail $f] [file size $f] bytes" }
