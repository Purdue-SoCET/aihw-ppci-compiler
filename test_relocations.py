#!/usr/bin/env python3
"""
Atalla Relocation Verification Script

Tests that JAL and JALR instructions correctly resolve to their intended targets.
Parses ELF symbol table and disassembly output to verify relocations.
"""
# Claude made this, had to change how it was parsing the header but it is good otherwise

import re
import json
from typing import Dict, List, Tuple, Optional

class ELFParser:
    """Parse ELF file to extract symbol table"""
    
    def __init__(self, elf_path: str):
        with open(elf_path, 'rb') as f:
            self.data = f.read()
        self.symbols = {}
        self.code_section_offset = 0x34  # Will be dynamically found
        self._find_code_section()
        self._parse_symbols()
    
    def _find_code_section(self):
        """Find the actual offset of the code section in the file"""
        shoff = int.from_bytes(self.data[0x20:0x24], 'little')
        shentsize = int.from_bytes(self.data[0x2E:0x30], 'little')
        shnum = int.from_bytes(self.data[0x30:0x32], 'little')
        shstrndx = int.from_bytes(self.data[0x32:0x34], 'little')
        
        # Read string table section header
        strtab_header_off = shoff + shstrndx * shentsize
        strtab_header = self.data[strtab_header_off : strtab_header_off + shentsize]
        strtab_offset = int.from_bytes(strtab_header[16:20], 'little')
        
        # Find "code" section
        for i in range(shnum):
            sh_offset = shoff + i * shentsize
            sh = self.data[sh_offset : sh_offset + shentsize]
            
            # Get section name
            name_offset = int.from_bytes(sh[0:4], 'little')
            name_start = strtab_offset + name_offset
            name_end = self.data.index(b'\x00', name_start)
            section_name = self.data[name_start:name_end].decode('ascii')
            
            if section_name == "code":
                # Get section offset in file
                self.code_section_offset = int.from_bytes(sh[16:20], 'little')
                print(f"✓ Found code section at file offset 0x{self.code_section_offset:04X}")
                break
    
    def _parse_symbols(self):
        """Extract symbol table from ELF and adjust addresses"""
        shoff = int.from_bytes(self.data[0x20:0x24], 'little')
        shentsize = int.from_bytes(self.data[0x2E:0x30], 'little')
        shnum = int.from_bytes(self.data[0x30:0x32], 'little')
        shstrndx = int.from_bytes(self.data[0x32:0x34], 'little')
        
        # Read string table section header
        strtab_header_off = shoff + shstrndx * shentsize
        strtab_header = self.data[strtab_header_off : strtab_header_off + shentsize]
        strtab_offset = int.from_bytes(strtab_header[16:20], 'little')
        
        # Find .symtab section
        for i in range(shnum):
            sh_offset = shoff + i * shentsize
            sh = self.data[sh_offset : sh_offset + shentsize]
            
            # Get section name
            name_offset = int.from_bytes(sh[0:4], 'little')
            name_start = strtab_offset + name_offset
            name_end = self.data.index(b'\x00', name_start)
            section_name = self.data[name_start:name_end].decode('ascii')
            
            if section_name == ".symtab":
                symtab_offset = int.from_bytes(sh[16:20], 'little')
                symtab_size = int.from_bytes(sh[20:24], 'little')
                symtab_entsize = int.from_bytes(sh[36:40], 'little')
                
                # Find .strtab for symbol names
                strtab_link = int.from_bytes(sh[24:28], 'little')
                strtab_sh_off = shoff + strtab_link * shentsize
                strtab_sh = self.data[strtab_sh_off : strtab_sh_off + shentsize]
                sym_strtab_offset = int.from_bytes(strtab_sh[16:20], 'little')
                
                # Parse symbol table
                for sym_i in range(0, symtab_size, symtab_entsize):
                    sym = self.data[symtab_offset + sym_i : symtab_offset + sym_i + symtab_entsize]
                    
                    sym_name_off = int.from_bytes(sym[0:4], 'little')
                    sym_value = int.from_bytes(sym[4:8], 'little')
                    sym_size = int.from_bytes(sym[8:12], 'little')
                    sym_info = sym[12]
                    sym_shndx = int.from_bytes(sym[14:16], 'little')
                    
                    # Get symbol name
                    if sym_name_off > 0:
                        name_start = sym_strtab_offset + sym_name_off
                        name_end = self.data.index(b'\x00', name_start)
                        sym_name = self.data[name_start:name_end].decode('ascii')
                        
                        # Store function symbols
                        sym_type = sym_info & 0xF
                        if sym_type == 2 or sym_value > 0:  # STT_FUNC or has value
                            # CRITICAL FIX: Add code section offset to get actual file address
                            actual_address = sym_value + self.code_section_offset
                            self.symbols[sym_name] = actual_address
                
                break
    
    def get_symbol_address(self, name: str) -> Optional[int]:
        """Get address of a symbol by name"""
        return self.symbols.get(name)
    
    def get_all_symbols(self) -> Dict[str, int]:
        """Get all symbols"""
        return self.symbols.copy()

class DisassemblyParser:
    """Parse disassembly output to extract jump instructions"""
    
    def __init__(self, disasm_path: str):
        with open(disasm_path, 'r') as f:
            self.lines = f.readlines()
        self.instructions = []
        self._parse()
    
    def _parse(self):
        """Extract all instructions with addresses and targets"""
        # Pattern: 0x0070    AB 00 06 00 00 00            jal        x1, 0xB8  # offset=12
        pattern = r'^(0x[0-9A-Fa-f]+)\s+([0-9A-Fa-f\s]+)\s+(jal|jalr|beq_s|bne_s|blt_s|bge_s|bgt_s|ble_s)\s+.*?(0x[0-9A-Fa-f]+)'
        
        for line in self.lines:
            match = re.search(pattern, line)
            if match:
                addr = int(match.group(1), 16)
                mnemonic = match.group(3)
                target = int(match.group(4), 16)
                
                self.instructions.append({
                    'address': addr,
                    'mnemonic': mnemonic,
                    'target': target,
                    'line': line.strip()
                })
    
    def get_jumps(self) -> List[Dict]:
        """Get all jump/branch instructions"""
        return self.instructions.copy()


class RelocationTester:
    """Test relocation correctness"""
    
    def __init__(self, elf_parser: ELFParser, disasm_parser: DisassemblyParser, config: Dict):
        self.elf = elf_parser
        self.disasm = disasm_parser
        self.config = config
        self.results = []
    
    def run_tests(self):
        """Run all relocation tests"""
        print("=" * 80)
        print("ATALLA RELOCATION VERIFICATION")
        print("=" * 80)
        print()
        
        # Show discovered symbols
        print("Discovered Symbols:")
        symbols = self.elf.get_all_symbols()
        for name, addr in sorted(symbols.items(), key=lambda x: x[1]):
            print(f"  {name:30s} @ 0x{addr:04X}")
        print()
        
        # Show discovered jumps
        jumps = self.disasm.get_jumps()
        print(f"Found {len(jumps)} jump/branch instructions")
        print()
        
        # Test each expected relocation
        print("=" * 80)
        print("TESTING RELOCATIONS")
        print("=" * 80)
        print()
        
        for test in self.config.get("expected_relocations", []):
            self._test_relocation(test, jumps, symbols)
        
        # Check for unexpected jumps
        self._check_unexpected_jumps(jumps)
        
        # Print summary
        self._print_summary()
    
    def _test_relocation(self, test: Dict, jumps: List[Dict], symbols: Dict[str, int]):
        """Test a single expected relocation"""
        reloc_type = test["type"]
        source_func = test.get("source_function")
        target_name = test["target"]
        should_succeed = test.get("should_succeed", True)
        
        # Find target address
        target_addr = symbols.get(target_name)
        if target_addr is None:
            print(f"❌ FAIL: Target '{target_name}' not found in symbol table")
            self.results.append(("FAIL", f"Missing target: {target_name}"))
            return
        
        # Find matching jump instruction
        matching_jumps = []
        for jump in jumps:
            if reloc_type.lower() in jump['mnemonic'].lower():
                # Check if in correct source function (optional)
                if source_func:
                    source_addr = symbols.get(source_func)
                    # Simple heuristic: jump is within ~200 bytes of function start
                    if source_addr and abs(jump['address'] - source_addr) < 200:
                        matching_jumps.append(jump)
                else:
                    matching_jumps.append(jump)
        
        # Check if any matching jump points to target
        found = False
        for jump in matching_jumps:
            if jump['target'] == target_addr:
                found = True
                status = "✅ PASS" if should_succeed else "⚠️  UNEXPECTED SUCCESS"
                msg = f"{reloc_type:6s} @ 0x{jump['address']:04X} → {target_name} (0x{target_addr:04X})"
                print(f"{status}: {msg}")
                self.results.append(("PASS" if should_succeed else "WARN", msg))
                
                # Mark jump as verified
                jump['verified'] = True
                break
        
        if not found:
            status = "❌ FAIL" if should_succeed else "✅ EXPECTED FAIL"
            msg = f"{reloc_type:6s} to {target_name} (0x{target_addr:04X})"
            print(f"{status}: {msg}")
            if matching_jumps:
                print(f"         Found {len(matching_jumps)} {reloc_type} instructions but none target 0x{target_addr:04X}")
                for j in matching_jumps[:3]:  # Show first 3
                    print(f"           0x{j['address']:04X} → 0x{j['target']:04X}")
            self.results.append(("FAIL" if should_succeed else "PASS", msg))
    
    def _check_unexpected_jumps(self, jumps: List[Dict]):
        """Check for jumps not in expected config"""
        print()
        print("=" * 80)
        print("UNVERIFIED JUMPS")
        print("=" * 80)
        print()
        
        unverified = [j for j in jumps if not j.get('verified')]
        
        if unverified:
            print(f"⚠️  Found {len(unverified)} unverified jump instructions:")
            for jump in unverified:
                # Try to find what symbol it points to
                target_name = "unknown"
                for name, addr in self.elf.get_all_symbols().items():
                    if addr == jump['target']:
                        target_name = name
                        break
                
                print(f"  {jump['mnemonic']:6s} @ 0x{jump['address']:04X} → 0x{jump['target']:04X} ({target_name})")
        else:
            print("✅ All jumps verified!")
    
    def _print_summary(self):
        """Print test summary"""
        print()
        print("=" * 80)
        print("SUMMARY")
        print("=" * 80)
        
        passes = sum(1 for r in self.results if r[0] == "PASS")
        fails = sum(1 for r in self.results if r[0] == "FAIL")
        warns = sum(1 for r in self.results if r[0] == "WARN")
        
        print(f"✅ PASSED: {passes}")
        print(f"❌ FAILED: {fails}")
        print(f"⚠️  WARNINGS: {warns}")
        print()
        
        if fails == 0:
            print("ALL TESTS PASSED!")
        else:
            print("❌ SOME TESTS FAILED")
            print("\nFailed tests:")
            for status, msg in self.results:
                if status == "FAIL":
                    print(f"  - {msg}")


def main():
    # Load configuration
    try:
        with open("relocation_tests.json", 'r') as f:
            config = json.load(f)
    except FileNotFoundError:
        print("⚠️  No relocation_tests.json found, using default config")
        config = {
            "expected_relocations": [
                {
                    "type": "JAL",
                    "source_function": "instruct_tests",
                    "target": "helper",
                    "should_succeed": True
                },
                {
                    "type": "JAL",
                    "source_function": "instruct_tests",
                    "target": "instruct_tests_epilog",
                    "should_succeed": True
                },
                {
                    "type": "JAL",
                    "source_function": "helper",
                    "target": "helper_epilog",
                    "should_succeed": True
                }
            ]
        }
    
    # Parse ELF and disassembly
    print("Parsing ELF file...")
    elf_parser = ELFParser("output.elf")
    
    print("Parsing disassembly...")
    disasm_parser = DisassemblyParser("disassembly.txt")
    
    # Run tests
    tester = RelocationTester(elf_parser, disasm_parser, config)
    tester.run_tests()


if __name__ == "__main__":
    main()