# GNU Make options end at --: make build -- --no-debug (also works for run).
# ARGS=--no-debug is equivalent; the Python builder accepts the flag directly.
BUILD_ARGS = $(ARGS) $(filter --no-debug,$(MAKECMDGOALS))
.PHONY: build release run shot verify toolchain extract clean --no-debug
--no-debug:

.DEFAULT_GOAL := build
build:
	python3 tools/build.py $(BUILD_ARGS)
release: build
	python3 tools/release.py
run: build
	bin/ukncbtl/uknc-play --rom bin/ukncbtl/uknc_rom.bin --disk build/darkroom.dsk
shot: build
	python3 tools/uknc_control.py boot --disk build/darkroom.dsk --wait 100 --shot tmp/start.png
verify: build
	python3 tools/verify.py
toolchain:
	python3 tools/build_toolchain.py
extract:
	node tools/extract.mjs
clean:
	python3 tools/clean.py
