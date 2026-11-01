#!/bin/sh
# Rebuilds icon-program.exe; needs MinGW-w64 (the Raven build container has it).
set -eu
cd "$(dirname "$0")"
x86_64-w64-mingw32-windres icon.rc -O coff -o icon.res
x86_64-w64-mingw32-gcc -Os -s -nostdlib -Wl,--entry,start -Wl,--subsystem,windows main.c icon.res -o icon-program.exe
rm icon.res
