#!/usr/bin/env python3

import argparse
import pathlib
import subprocess
import sys
from typing import List

PYTHON = sys.executable


def run_cmd(cmd: List[str], verbose: bool = False) -> None:
	if verbose:
		print("+", " ".join(cmd))
	subprocess.run(cmd, check=True)


def source_to_output(source: str, suffix: str) -> str:
	return str(pathlib.Path(source).with_suffix(suffix))


def parse_args() -> argparse.Namespace:
	parser = argparse.ArgumentParser(
		description=(
			"Compile and link C sources for Atalla using PPCI, matching the "
			"project Makefile flow."
		)
	)
	parser.add_argument("sources", nargs="+", help="Input C source files")
	parser.add_argument(
		"-S",
		dest="emit_asm",
		action="store_true",
		help="Compile sources to assembly only",
	)
	parser.add_argument(
		"-c",
		dest="emit_obj",
		action="store_true",
		help="Compile sources to object files only",
	)
	parser.add_argument(
		"-o",
		dest="output",
		default=None,
		help="Output file name (single-source compile or final linked ELF)",
	)
	parser.add_argument(
		"-m",
		dest="arch",
		default="atalla",
		help="Target architecture (default: atalla)",
	)
	parser.add_argument(
		"-O",
		dest="opt_level",
		default="2",
		help="Optimization level without the leading O (default: 2)",
	)
	parser.add_argument(
		"--super-verbose",
		dest="super_verbose",
		action="store_true",
		help="Pass --super-verbose to the PPCI compiler",
	)
	parser.add_argument(
		"--dis",
		dest="run_dump_dis",
		action="store_true",
		help="Run dump_elf.py and disassemble.py after linking",
	)
	parser.add_argument(
		"--test-reloc",
		dest="test_reloc",
		action="store_true",
		help="Run test_relocations.py after build steps",
	)
	parser.add_argument(
		"--verbose",
		dest="verbose",
		action="store_true",
		help="Print commands before running",
	)
	parser.add_argument(
		"--cc-flag",
		dest="cc_flags",
		action="append",
		default=[],
		help="Extra flag to pass to each compiler invocation (repeatable)",
	)
	parser.add_argument(
		"--ld-flag",
		dest="ld_flags",
		action="append",
		default=[],
		help="Extra flag to pass to linker invocation (repeatable)",
	)

	args = parser.parse_args()
	if args.emit_asm and args.emit_obj:
		parser.error("Use either -S or -c, not both.")
	if args.output and len(args.sources) > 1 and (args.emit_asm or args.emit_obj):
		parser.error("-o with -S/-c and multiple sources is ambiguous. Use one source.")
	return args


def compiler_base(args: argparse.Namespace) -> List[str]:
	base = [
		PYTHON,
		"-m",
		"ppci",
		"atalla_cc",
		"-m",
		args.arch,
		f"-O{args.opt_level}",
	]
	if args.super_verbose:
		base.append("--super-verbose")
	base.extend(args.cc_flags)
	return base


def compile_source(
	args: argparse.Namespace, source: str, mode_flag: str, output_file: str
) -> None:
	cmd = compiler_base(args) + [source, mode_flag, "-o", output_file]
	run_cmd(cmd, args.verbose)


def compile_to_asm(args: argparse.Namespace) -> None:
	for source in args.sources:
		output_file = args.output if args.output and len(args.sources) == 1 else source_to_output(source, ".s")
		compile_source(args, source, "-S", output_file)


def compile_to_objects(args: argparse.Namespace) -> List[str]:
	object_files: List[str] = []
	for source in args.sources:
		output_file = args.output if args.output and len(args.sources) == 1 else source_to_output(source, ".o")
		compile_source(args, source, "-c", output_file)
		object_files.append(output_file)
	return object_files


def link_objects(args: argparse.Namespace, object_files: List[str]) -> None:
	output_elf = args.output or "output.elf"
	cmd = [PYTHON, "-m", "ppci", "ld", *object_files, "-o", output_elf, *args.ld_flags]
	run_cmd(cmd, args.verbose)


def run_post_steps(args: argparse.Namespace) -> None:
	if args.run_dump_dis:
		run_cmd([PYTHON, "dump_elf.py"], args.verbose)
		run_cmd([PYTHON, "disassemble.py"], args.verbose)
	if args.test_reloc:
		run_cmd([PYTHON, "test_relocations.py"], args.verbose)


def main() -> int:
	args = parse_args()

	if args.emit_asm:
		compile_to_asm(args)
		run_post_steps(args)
		return 0

	object_files = compile_to_objects(args)
	if not args.emit_obj:
		link_objects(args, object_files)

	run_post_steps(args)
	return 0


if __name__ == "__main__":
	try:
		raise SystemExit(main())
	except subprocess.CalledProcessError as exc:
		print(f"Command failed with exit code {exc.returncode}", file=sys.stderr)
		raise SystemExit(exc.returncode)
