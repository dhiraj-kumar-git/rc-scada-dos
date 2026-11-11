# Run from the repo root.
#   make test               full toolchain check on the synthetic fixture
#   make all CONFIG=config.json   the same pipeline on the real Coimbra data
CONFIG ?= config.json
PY     ?= python3

.PHONY: all test data rules demo sim host arm-check bench clean

all: data rules demo sim host

data:
	$(PY) python/extract.py $(CONFIG)

rules:
	$(PY) python/train_rules.py $(CONFIG)

demo:
	$(PY) python/make_demo.py $(CONFIG)

sim:
	mkdir -p build
	iverilog -g2005 -I rtl -o build/tb_replay.vvp tb/tb_replay.v rtl/replay_top.v rtl/detector.v
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
