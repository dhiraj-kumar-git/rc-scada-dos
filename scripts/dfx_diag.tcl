# E2 DFX flow (non-project, UG909), based on scripts/dfx_smoke.tcl: static
# design diag_top with the partition u_rm as a black box, three modules
# (rm_detector, rm_net_diag, rm_modbus_diag) synthesised out of context, three
# routed configurations, full and partial bitstreams, pr_verify across all three.
# Run from the repo root (on this laptop start Vivado with -nolog):
#   vivado -mode batch -nolog -source scripts/dfx_diag.tcl
# Outputs in build/dfx_diag/; prints DFX_DIAG_RESULT lines.
set root [file normalize [file join [file dirname [info script]] ..]]
set out  [file join $root build dfx_diag]
set part xc7z020clg484-1
set rtl  [file join $root rtl]
file mkdir $out
set memfile [file join $rtl records.mem]

# 1. static design, rm_slot as a black box
read_verilog [list [file join $rtl diag_top.v] [file join $rtl rm_slot_bb.v]]
synth_design -top diag_top -part $part -include_dirs $rtl -generic "MEMFILE=\"$memfile\""
write_checkpoint -force [file join $out static_synth.dcp]
close_project

# 2. the three modules, out of context
set mods {rm_detector rm_net_diag rm_modbus_diag}
foreach m $mods {
    read_verilog [list [file join $rtl $m.v] [file join $rtl rm_core.v] [file join $rtl detector.v] [file join $rtl sketch.v]]
    synth_design -mode out_of_context -top rm_slot -part $part -include_dirs $rtl
    write_checkpoint -force [file join $out ${m}_synth.dcp]
    close_project
}

proc finish_config {out name} {
    report_utilization -file [file join $out ${name}_utilization.txt]
    report_utilization -pblocks [get_pblocks pblock_rm] -file [file join $out ${name}_pblock_utilization.txt]
    report_timing_summary -file [file join $out ${name}_timing.txt]
    set wns [get_property SLACK [get_timing_paths -max_paths 1 -nworst 1 -setup]]
    puts "DFX_DIAG_RESULT config $name wns_ns=$wns"
    write_checkpoint -force [file join $out ${name}_routed.dcp]
    write_bitstream -force [file join $out $name]
}

# 3. configuration 1: static + rm_detector; then lock the static routing
open_checkpoint [file join $out static_synth.dcp]
read_checkpoint -cell u_rm [file join $out rm_detector_synth.dcp]
set_property HD.RECONFIGURABLE true [get_cells u_rm]
read_xdc [file join $root constraints zedboard_replay.xdc]
read_xdc [file join $root dfx_smoke dfx_diag_pblock.xdc]
opt_design
place_design
route_design
finish_config $out config_detector
update_design -cell u_rm -black_box
lock_design -level routing
write_checkpoint -force [file join $out static_routed.dcp]
close_project

# 4. configurations 2 and 3 on the same locked static design
foreach {m name} {rm_net_diag config_net_diag rm_modbus_diag config_modbus_diag} {
    open_checkpoint [file join $out static_routed.dcp]
    read_checkpoint -cell u_rm [file join $out ${m}_synth.dcp]
    opt_design
    place_design
    route_design
    finish_config $out $name
    close_project
}

# 5. the static design must be identical in all three
pr_verify -initial [file join $out config_detector_routed.dcp] \
    -additional [list [file join $out config_net_diag_routed.dcp] [file join $out config_modbus_diag_routed.dcp]] \
    -file [file join $out pr_verify.txt]
puts "DFX_DIAG_RESULT done: bitstreams in build/dfx_diag, pr_verify report in build/dfx_diag/pr_verify.txt"
foreach f [lsort [glob -nocomplain -directory $out *.bit]] { puts "DFX_DIAG_RESULT bitstream [file tail $f] [file size $f] bytes" }
