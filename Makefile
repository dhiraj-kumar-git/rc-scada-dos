# Run from the repo root.
#   make test               full toolchain check on the synthetic fixture
#   make all CONFIG=config.json   the same pipeline on the real Coimbra data
CONFIG ?= config.json
PY     ?= python3

.PHONY: all test data rules demo sim host arm-check bench sketch sketch-vec sketch-host modules-sim clean

all: data rules demo sim host

data:
	$(PY) python/extract.py $(CONFIG)

rules:
	$(PY) python/train_rules.py $(CONFIG)

demo:
	$(PY) python/make_demo.py $(CONFIG)

sim:
	mkdir -p build
	iverilog -g2005 -I rtl -o build/tb_replay.vvp tb/tb_replay.v rtl/replay_top.v rtl/detector.v rtl/sketch.v
	vvp -n build/tb_replay.vvp
	$(PY) python/compare.py sim

host:
	mkdir -p build
	gcc -O2 -Wall -Ic -o build/host c/host_main.c c/detector.c
	./build/host
	$(PY) python/compare.py host

# ARM Cortex-A9 build of the same C code, run under QEMU: checks correctness
# on the ARM instruction set without a board (timing under QEMU is meaningless)
arm-check:
	mkdir -p build
	arm-linux-gnueabihf-gcc -O2 -static -mcpu=cortex-a9 -mfpu=neon -mfloat-abi=hard -Wall -Ic -DOUT_PREFIX='"arm"' -o build/arm_host c/host_main.c c/detector.c
	qemu-arm build/arm_host
	$(PY) python/compare.py arm

# sketch (E1): stress vectors through rtl/sketch.v alone, D = 1, 2, 4, 8
sketch-vec:
	mkdir -p build
	$(PY) tests/make_sketch_vectors.py
	for d in 1 2 4 8; do \
	  iverilog -g2005 -I rtl -I build -DSKETCH_D=$$d -o build/tb_sketch_d$$d.vvp tb/tb_sketch.v rtl/sketch.v && \
	  vvp -n build/tb_sketch_d$$d.vvp || exit 1; done
	$(PY) python/compare.py sketch-vec

# sketch on the demo regions inside replay_top, D = 1, 2, 4, 8: windows, LEDs and cycles
sketch:
	mkdir -p build
	for d in 1 2 4 8; do \
	  iverilog -g2005 -I rtl -DSKETCH -DSKETCH_D=$$d -o build/tb_replay_sk$$d.vvp tb/tb_replay.v rtl/replay_top.v rtl/detector.v rtl/sketch.v && \
	  vvp -n build/tb_replay_sk$$d.vvp | grep '^region' | tee build/sketch_sim_d$$d.txt && \
	  $(PY) python/compare.py sim | tail -3 || exit 1; done
	$(PY) python/compare.py sketch

# C sketch on the PC against the golden model, D = 1, 2, 4, 8
sketch-host:
	mkdir -p build
	gcc -O2 -Wall -Ic -o build/sketch_check c/sketch_check_main.c c/sketch_bench.c
	./build/sketch_check
	$(PY) python/compare.py sketch-host

# DFX modules (E2) through the static top diag_top, one module at a time
MOD_SRC = rtl/diag_top.v rtl/rm_core.v rtl/detector.v rtl/sketch.v
modules-sim:
	mkdir -p build
	iverilog -g2005 -I rtl -DRM_ID=1 -o build/tb_diag_m1.vvp tb/tb_diag.v rtl/rm_detector.v $(MOD_SRC)
	vvp -n build/tb_diag_m1.vvp | grep '^rm='
	iverilog -g2005 -I rtl -DRM_ID=2 -o build/tb_diag_m2.vvp tb/tb_diag.v rtl/rm_net_diag.v $(MOD_SRC)
	vvp -n build/tb_diag_m2.vvp | grep '^rm='
	iverilog -g2005 -I rtl -DRM_ID=3 -o build/tb_diag_m3.vvp tb/tb_diag.v rtl/rm_modbus_diag.v $(MOD_SRC)
	vvp -n build/tb_diag_m3.vvp | grep '^rm='
	$(PY) python/compare.py modules

# per-packet work benchmark on this PC (plain counting vs sketch rows)
bench:
	mkdir -p build
	gcc -O2 -Wall -Ic -o build/sketch_bench c/sketch_host_main.c c/sketch_bench.c
	./build/sketch_bench

# runs in a separate copy (selftest/) so it never overwrites the real
# generated files in rtl/ and c/
test:
	rm -rf selftest && mkdir -p selftest
	cp -r python rtl tb c tests Makefile selftest/
	cd selftest && $(PY) tests/make_fixture.py && $(MAKE) all CONFIG=config_fixture.json

clean:
	rm -rf build selftest data_fixture config_fixture.json
