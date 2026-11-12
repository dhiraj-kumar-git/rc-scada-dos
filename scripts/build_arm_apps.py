"""Build the two bare-metal ARM programs with the Vitis Python interface.

Run from the repo root on Windows, after scripts/build_arm_platform.tcl:
    vitis -s scripts/build_arm_apps.py
Workspace: ../vitis_ws (next to the repo). Outputs:
    build/zynq_main.elf        detector on the ARM (c/zynq_main.c, detector.c, rules.h, records.h)
    build/sketch_zynq_main.elf per-packet work benchmark (c/sketch_zynq_main.c, sketch_bench.c)
Both are built from the Hello World template, with helloworld.c replaced and -O2.
"""
import os
import shutil

import vitis

ROOT = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
XSA = os.path.join(ROOT, "build", "arm_platform.xsa")
WS = os.path.normpath(os.path.join(ROOT, "..", "vitis_ws"))
CDIR = os.path.join(ROOT, "c")
PLATFORM = "zed_ps_platform"
DOMAIN = "standalone_ps7_cortexa9_0"
APPS = {
    "zynq_main": ["zynq_main.c", "detector.c", "detector.h", "rules.h", "records.h"],
    "sketch_zynq_main": ["sketch_zynq_main.c", "sketch_bench.c", "sketch_bench.h"],
}

if not os.path.isfile(XSA):
    raise SystemExit("missing %s: run scripts/build_arm_platform.tcl first" % XSA)
if os.path.isdir(WS):
    shutil.rmtree(WS)

client = vitis.create_client()
client.set_workspace(WS)

platform = client.create_platform_component(name=PLATFORM, hw_design=XSA, os="standalone",
                                            cpu="ps7_cortexa9_0", domain_name=DOMAIN,
                                            generate_dtb=False)  # bare metal: no Linux device tree needed
platform.build()
xpfm = client.find_platform_in_repos(PLATFORM)
print("ARM_APPS platform built:", xpfm)

for app_name, files in APPS.items():
    app = client.create_app_component(name=app_name, platform=xpfm, domain=DOMAIN, template="hello_world")
    app.remove_files(files=["src/helloworld.c"])
    app.import_files(from_loc=CDIR, files=files, dest_dir_in_cmp="src")
    app.set_app_config(key="USER_COMPILE_OPTIMIZATION_LEVEL", values="-O2")
    print("ARM_APPS", app_name, "optimization:", app.get_app_config(key="USER_COMPILE_OPTIMIZATION_LEVEL"))
    app.build()
    elf = os.path.join(WS, app_name, "build", app_name + ".elf")
    if not os.path.isfile(elf):
        raise SystemExit("ARM_APPS FAIL: %s not found after build" % elf)
    dst = os.path.join(ROOT, "build", app_name + ".elf")
    shutil.copyfile(elf, dst)
    print("ARM_APPS_RESULT %s %d bytes" % (os.path.relpath(dst, ROOT).replace("\\", "/"), os.path.getsize(dst)))

vitis.dispose()
