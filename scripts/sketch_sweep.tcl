# Out-of-context synthesis and implementation of rtl/sketch.v for D = 1, 2, 4, 8
# at a 10 ns (100 MHz) clock. Writes results/sketch_sweep.txt and prints
# SKETCH_SWEEP lines. Run from the repo root:
#   vivado -mode batch -nolog -source scripts/sketch_sweep.tcl
set root [file normalize [file join [file dirname [info script]] ..]]
set part xc7z020clg484-1
set out  [file join $root build sketch_sweep]
file mkdir $out
set res [open [file join $root results sketch_sweep.txt] w]
puts $res "# rtl/sketch.v alone, out-of-context, $part, Vivado [version -short], clock 10 ns"
puts $res "# D WNS_ns LUTs FFs RAMB36 RAMB18 DSP48 timing"

proc util_count {pattern} {
    return [llength [get_cells -hierarchical -quiet -filter "REF_NAME =~ $pattern"]]
}

foreach d {1 2 4 8} {
    read_verilog [file join $root rtl sketch.v]
    synth_design -mode out_of_context -top sketch -part $part -generic D=$d
    create_clock -period 10.000 -name clk [get_ports clk]
    opt_design
    place_design
    route_design
    report_timing_summary -file [file join $out timing_d$d.txt]
    report_utilization -file [file join $out utilization_d$d.txt]
    set wns  [get_property SLACK [get_timing_paths -max_paths 1 -nworst 1 -setup]]
    set luts [llength [get_cells -hierarchical -quiet -filter {PRIMITIVE_GROUP == LUT}]]
    set ffs  [llength [get_cells -hierarchical -quiet -filter {PRIMITIVE_GROUP == FLOP_LATCH}]]
    set b36  [util_count RAMB36*]
    set b18  [util_count RAMB18*]
    set dsp  [util_count DSP48*]
    set ok   [expr {$wns >= 0 ? "met" : "FAILED"}]
    puts $res "$d $wns $luts $ffs $b36 $b18 $dsp $ok"
    puts "SKETCH_SWEEP D=$d wns_ns=$wns luts=$luts ffs=$ffs ramb36=$b36 ramb18=$b18 dsp=$dsp timing=$ok"
    close_project
}
close $res
